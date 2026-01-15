// chartDataProcessor.js
// Utility functions for processing chart data

/**
 * Load and clean features from unified data
 * @param {Array} data - Array of data objects
 * @returns {Object} - Cleaned data with feature columns
 */
export function loadAndCleanFeatures(data) {
    if (!data || data.length === 0) {
        return { data: [], columns: [] };
    }

    // Convert to DataFrame-like structure
    const df = data;

    // Exclude non-feature columns
    const excluded = new Set(['date_key', 'date_numeric', 'plant', 'plant_num', 'cluster', 'cluster_num', 'mutation']);

    // Get all columns from first row
    const allColumns = Object.keys(df[0] || {});

    // Filter to numeric feature columns
    const featureColumns = allColumns.filter(col => {
        if (excluded.has(col)) return false;

        // Check if column is numeric (has numeric values)
        const sampleValues = df.slice(0, 100).map(row => row[col]).filter(v => v != null);
        if (sampleValues.length === 0) return false;

        const numericCount = sampleValues.filter(v => {
            const num = Number(v);
            return !isNaN(num) && isFinite(num);
        }).length;

        return numericCount / sampleValues.length > 0.5; // At least 50% numeric
    });

    // Filter data to only include feature columns + identifiers
    const keepColumns = ['plant', 'date_key', 'plant_num', 'mutation', ...featureColumns];
    const cleanedData = df.map(row => {
        const cleaned = {};
        keepColumns.forEach(col => {
            const val = row[col];
            if (val == null || val === '') {
                cleaned[col] = null;
            } else {
                const num = Number(val);
                cleaned[col] = isNaN(num) ? val : num;
            }
        });
        return cleaned;
    });

    // Calculate median for each column for imputation
    const medians = {};
    featureColumns.forEach(col => {
        const values = cleanedData.map(row => row[col]).filter(v => v != null && isFinite(v));
        if (values.length > 0) {
            values.sort((a, b) => a - b);
            medians[col] = values[Math.floor(values.length / 2)];
        }
    });

    // Impute missing values with median
    cleanedData.forEach(row => {
        featureColumns.forEach(col => {
            if (row[col] == null || !isFinite(row[col])) {
                row[col] = medians[col] || 0;
            }
        });
    });

    return {
        data: cleanedData,
        columns: keepColumns,
        featureColumns: featureColumns
    };
}

/**
 * Merge genotype mapping with features data
 * @param {Array} featuresData - Array of feature objects
 * @param {Array} genotypeMapping - Array of genotype mapping objects
 * @returns {Array} - Merged data with mutation groups
 */
export function mergeGenotypeMapping(featuresData, genotypeMapping) {
    if (!genotypeMapping || genotypeMapping.length === 0) {
        return featuresData;
    }

    // Create lookup map
    const mappingMap = {};
    genotypeMapping.forEach(item => {
        const plantName = item.plant || item.Plant_Name;
        if (plantName) {
            mappingMap[plantName] = item.mutation || item.Mutation_Group;
        }
        // Also map by plant_num if available
        if (item.Plant_Number) {
            mappingMap[`num_${item.Plant_Number}`] = item.mutation || item.Mutation_Group;
        }
    });

    // Merge mutation groups
    return featuresData.map(row => {
        const plant = row.plant;
        let mutation = mappingMap[plant];

        // Try plant_num if plant name didn't match
        if (!mutation && row.plant_num) {
            mutation = mappingMap[`num_${row.plant_num}`];
        }

        return {
            ...row,
            mutation: mutation || null
        };
    });
}

/**
 * Split features into categories (Vegetation, Texture, Morphology)
 * @param {Array} columns - Array of column names
 * @returns {Object} - Object with categorized feature lists
 */
export function splitFeatureGroups(columns) {
    const vegKeys = ['ndvi', 'gndvi', 'rdvi', 'mcari', 'tcari', 'savi', 'osavi', 'evi', 'ari', 'pvi', 'dvi', 'ccci', 'cire', 'msavi', 'wdvi', 'lci'];
    const texKeys = ['hog', 'lbp', 'lac', 'ehd', 'texture_'];
    const morphKeys = ['morph_', 'height', 'width', 'area', 'perimeter', 'circularity', 'extent', 'solidity', 'eccentricity', 'equivalent_diameter', 'roundness', 'bbox', 'convex'];

    const veg = [];
    const tex = [];
    const morph = [];

    columns.forEach(col => {
        const colLower = col.toLowerCase();
        if (col.startsWith('veg_') || vegKeys.some(k => colLower.includes(k))) {
            veg.push(col);
        } else if (col.startsWith('texture_') || texKeys.some(k => colLower.includes(k))) {
            tex.push(col);
        } else if (col.startsWith('morph_') || morphKeys.some(k => colLower.includes(k))) {
            morph.push(col);
        }
    });

    return {
        Vegetation: veg,
        Texture: tex,
        Morphology: morph
    };
}

/**
 * Compute Pearson correlation matrix
 * @param {Array} data - Array of data objects
 * @param {Array} columns - Array of column names to correlate
 * @returns {Array} - 2D correlation matrix
 */
export function computeCorrelationMatrix(data, columns) {
    if (!data || data.length === 0 || !columns || columns.length === 0) {
        return { matrix: [], columns: [] };
    }

    // Extract values for each column
    const values = {};
    columns.forEach(col => {
        values[col] = data.map(row => {
            const val = row[col];
            return (val != null && isFinite(val)) ? val : 0;
        });
    });

    // Compute correlation matrix
    const matrix = columns.map(col1 => {
        return columns.map(col2 => {
            if (col1 === col2) return 1.0;

            const x = values[col1];
            const y = values[col2];

            // Calculate mean
            const meanX = x.reduce((a, b) => a + b, 0) / x.length;
            const meanY = y.reduce((a, b) => a + b, 0) / y.length;

            // Calculate correlation
            let numerator = 0;
            let sumSqX = 0;
            let sumSqY = 0;

            for (let i = 0; i < x.length; i++) {
                const dx = x[i] - meanX;
                const dy = y[i] - meanY;
                numerator += dx * dy;
                sumSqX += dx * dx;
                sumSqY += dy * dy;
            }

            const denominator = Math.sqrt(sumSqX * sumSqY);
            return denominator > 0 ? numerator / denominator : 0;
        });
    });

    return { matrix, columns };
}

/**
 * Prepare data for violin plots
 * @param {Array} data - Array of data objects
 * @param {Object} featureGroups - Object with categorized features
 * @returns {Array} - Long format data for violin plots
 */
export function prepareViolinData(data, featureGroups) {
    const result = [];

    Object.keys(featureGroups).forEach(category => {
        const features = featureGroups[category];
        if (!features || features.length === 0) return;

        features.forEach(feature => {
            data.forEach(row => {
                if (row.mutation && row[feature] != null && isFinite(row[feature])) {
                    result.push({
                        plant: row.plant,
                        mutation: row.mutation,
                        feature: feature,
                        value: row[feature],
                        category: category
                    });
                }
            });
        });
    });

    return result;
}

/**
 * Prepare data for boxplots
 * @param {Array} data - Array of data objects
 * @param {Array} features - Array of feature names to plot
 * @returns {Object} - Data grouped by mutation and feature
 */
export function prepareBoxplotData(data, features) {
    const result = {};

    features.forEach(feature => {
        result[feature] = {};

        data.forEach(row => {
            if (row.mutation && row[feature] != null && isFinite(row[feature])) {
                if (!result[feature][row.mutation]) {
                    result[feature][row.mutation] = [];
                }
                result[feature][row.mutation].push(row[feature]);
            }
        });
    });

    return result;
}

/**
 * Z-score normalization within feature
 * @param {Array} data - Array of data objects
 * @param {Array} columns - Columns to normalize
 * @returns {Array} - Normalized data
 */
export function zscoreNormalize(data, columns) {
    const result = data.map(row => ({ ...row }));

    columns.forEach(col => {
        const values = result.map(r => r[col]).filter(v => v != null && isFinite(v));
        if (values.length === 0) return;

        const mean = values.reduce((a, b) => a + b, 0) / values.length;
        const variance = values.reduce((sum, v) => sum + Math.pow(v - mean, 2), 0) / values.length;
        const std = Math.sqrt(variance);

        if (std > 0) {
            result.forEach(row => {
                if (row[col] != null && isFinite(row[col])) {
                    row[col] = (row[col] - mean) / std;
                }
            });
        }
    });

    return result;
}


