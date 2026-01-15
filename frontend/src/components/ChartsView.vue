<template>
  <div class="charts-view">
    <div class="charts-layout">
      <!-- Plot Space (Left) -->
      <div class="plot-space">
        <div v-if="!selectedChartType && !isInitialLoading" class="plot-placeholder">
          <p>Select a chart type from the panel on the right to display data</p>
        </div>
        <div v-else>
          <div id="plotly-chart" class="plotly-container"></div>
        </div>
        
        <!-- Loading Overlay -->
        <div v-if="isLoading || isInitialLoading" class="loading-overlay">
          <div class="loading-indicator-container">
            <p class="loading-text">
              <span v-if="selectedChartType"> Generating {{ getChartTypeName(selectedChartType) }}...</span>
              <span v-else>Loading data...</span>
            </p>
            <br> 
            <div class="loader"></div>
          </div>
        </div>

      </div>

      <!-- Selection Pane (Right) -->
      <div class="selection-pane">
        <h3 class="pane-title">Chart Selection</h3>
        <div class="chart-type-selector">
          <label class="selector-label">Chart Type:</label>
          <select v-model="selectedChartType" @change="onChartTypeChange" class="chart-select">
            <option value="">-- Select Chart Type --</option>
            <option value="correlation_all">Correlation Heatmap (All)</option>
            <option value="correlation_vegetation">Correlation Heatmap (Vegetation)</option>
            <option value="correlation_texture">Correlation Heatmap (Texture)</option>
            <option value="correlation_morphology">Correlation Heatmap (Morphology)</option>
            <option value="nested_pie">Nested Pie Chart</option>
            <option value="side_by_side_pie">Side-by-Side Pie Charts</option>
            <option value="violin">Violin Plots</option>
            <option value="boxplot">Boxplots</option>
            <option value="pca_2d">PCA 2D</option>
            <option value="pca_3d">PCA 3D</option>
            <option value="tsne_2d">t-SNE 2D</option>
            <option value="tsne_3d">t-SNE 3D</option>
          </select>
        </div>

        <div class="species-selector">
          <label class="selector-label">Species:</label>
          <select v-model="selectedSpecies" @change="onSpeciesChange" class="chart-select">
            <option value="">-- All Species --</option>
            <option v-for="species in availableSpecies" :key="species" :value="species">
              {{ species }}
            </option>
          </select>
        </div>

        <div v-if="selectedChartType && plotInstance" class="download-section">
          <button 
            @click="downloadChart" 
            class="download-button"
            title="Download chart as PNG"
          >
            Download Chart
          </button>
        </div>

        <!-- <div v-if="isLoading" class="loading-message">
          <p>Loading data...</p>
        </div> -->

        <div v-if="errorMessage" class="error-message">
          <p>{{ errorMessage }}</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import Plotly from 'plotly.js-dist-min';
import { getChartsData, getGenotypeMapping, getAvailablePlants, getPCA, getTSNE } from '../api';
import {
  loadAndCleanFeatures,
  mergeGenotypeMapping,
  splitFeatureGroups,
  computeCorrelationMatrix,
  prepareViolinData,
  prepareBoxplotData,
  zscoreNormalize
} from '../utils/chartDataProcessor';

export default {
  name: 'ChartsView',
  data() {
    return {
      selectedChartType: '',
      selectedSpecies: '',
      availableSpecies: [],
      rawData: null,
      processedData: null,
      genotypeMapping: null,
      isLoading: false,
      isInitialLoading: true,
      errorMessage: '',
      plotInstance: null
    };
  },
  async mounted() {
    await this.loadAvailableSpecies();
    await this.loadData();
  },
  methods: {
    async loadAvailableSpecies() {
      try {
        const response = await getAvailablePlants();
        this.availableSpecies = response.species || [];
      } catch (error) {
        console.error('Error loading available species:', error);
        // Fallback to common species if API fails
        this.availableSpecies = ['Sorghum', 'Cotton', 'Corn'];
      }
    },
    
    async loadData() {
      this.isLoading = true;
      this.errorMessage = '';
      
      try {
        // Load unified data and genotype mapping in parallel
        const [dataResponse, mappingResponse] = await Promise.all([
          getChartsData(this.selectedSpecies || null),
          getGenotypeMapping()
        ]);
        
        this.rawData = dataResponse.data || [];
        this.genotypeMapping = mappingResponse.mapping || [];
        
        // Process and merge data
        const cleaned = loadAndCleanFeatures(this.rawData);
        this.processedData = mergeGenotypeMapping(cleaned.data, this.genotypeMapping);
        
        // Set loading to false BEFORE rendering chart so the DOM element exists
        this.isLoading = false;
        this.isInitialLoading = false;
        
        // Wait for DOM to update before rendering chart
        await this.$nextTick();
        
        // If a chart is already selected, re-render it
        if (this.selectedChartType) {
          this.renderChart();
        }
      } catch (error) {
        console.error('Error loading chart data:', error);
        this.errorMessage = 'Failed to load chart data. Please try again.';
        this.isLoading = false;
        this.isInitialLoading = false;
      }
    },
    
    onSpeciesChange() {
      // Clear existing chart when species changes
      this.clearChart();
      // Reload data when species changes
      this.loadData();
    },
    
    async onChartTypeChange() {
      // Clear existing chart when switching chart types
      this.clearChart();
      
      if (this.selectedChartType) {
        // Show loading overlay
        this.isLoading = true;
        await this.$nextTick();
        
        if (this.processedData && this.processedData.length > 0) {
          // Data is already loaded, render immediately
          try {
            await this.renderChart();
          } finally {
            this.isLoading = false;
          }
        } else {
          // Data not loaded yet, wait for loadData to complete
          // isLoading will be managed by loadData
        }
      } else {
        this.isLoading = false;
      }
    },
    
    clearChart() {
      // Clear any existing Plotly chart
      const plotElement = document.getElementById('plotly-chart');
      if (plotElement) {
        try {
          Plotly.purge(plotElement);
          this.plotInstance = null;
        } catch (error) {
          console.warn('Error clearing chart:', error);
        }
      }
    },
    
    async downloadChart() {
      if (!this.plotInstance) {
        console.warn('No chart instance available for download');
        return;
      }
      
      const plotElement = document.getElementById('plotly-chart');
      if (!plotElement) {
        console.warn('Plot element not found');
        return;
      }
      
      // Temporarily set white background for download
      await Plotly.relayout(plotElement, {
        'paper_bgcolor': 'white'
      });
      
      // Wait a moment for the layout to update
      await new Promise(resolve => setTimeout(resolve, 100));
      
      const chartName = this.getChartTypeName(this.selectedChartType).replace(/\s+/g, '_');
      const filename = `${chartName}_${new Date().toISOString().split('T')[0]}.png`;
      
      try {
        // Download with white background
        await Plotly.downloadImage(plotElement, {
          format: 'png',
          width: 1200,
          height: 900,
          filename: filename
        });
      } finally {
        // Always restore original transparent background
        await Plotly.relayout(plotElement, {
          'paper_bgcolor': 'rgba(0,0,0,0)'
        });
      }
    },
    
    async renderChart() {
      if (!this.processedData || this.processedData.length === 0) {
        this.errorMessage = 'No data available to render chart';
        return;
      }
      
      // Clear any existing chart
      this.clearChart();
      
      // Ensure the DOM element exists before rendering
      await this.$nextTick();
      const plotElement = document.getElementById('plotly-chart');
      if (!plotElement) {
        console.error('Plotly chart container not found in DOM');
        this.errorMessage = 'Chart container not available. Please try again.';
        return;
      }
      
      await this.renderChartInternal();
    },
    
    async renderChartInternal() {
      try {
        switch (this.selectedChartType) {
          case 'correlation_all':
          case 'correlation_vegetation':
          case 'correlation_texture':
          case 'correlation_morphology':
            this.renderCorrelationHeatmap();
            break;
          case 'nested_pie':
            this.renderNestedPieChart();
            break;
          case 'side_by_side_pie':
            this.renderSideBySidePieCharts();
            break;
          case 'violin':
            this.renderViolinPlots();
            break;
          case 'boxplot':
            this.renderBoxplots();
            break;
          case 'pca_2d':
            await this.renderPCA2D();
            break;
          case 'pca_3d':
            await this.renderPCA3D();
            break;
          case 'tsne_2d':
            await this.renderTSNE2D();
            break;
          case 'tsne_3d':
            await this.renderTSNE3D();
            break;
        }
      } catch (error) {
        console.error('Error rendering chart:', error);
        this.errorMessage = `Error rendering chart: ${error.message}`;
        throw error;
      }
    },
    
    renderCorrelationHeatmap() {
      const cleaned = loadAndCleanFeatures(this.processedData);
      const featureGroups = splitFeatureGroups(cleaned.featureColumns);
      
      let columns = cleaned.featureColumns;
      const type = this.selectedChartType;
      
      if (type === 'correlation_vegetation') {
        columns = featureGroups.Vegetation;
      } else if (type === 'correlation_texture') {
        columns = featureGroups.Texture;
      } else if (type === 'correlation_morphology') {
        columns = featureGroups.Morphology;
      }
      
      if (columns.length < 2) {
        this.errorMessage = 'Not enough features for correlation matrix';
        return;
      }
      
      const { matrix, columns: corrColumns } = computeCorrelationMatrix(cleaned.data, columns);
      
      // Create triangular mask
      const mask = [];
      for (let i = 0; i < matrix.length; i++) {
        mask.push([]);
        for (let j = 0; j < matrix[i].length; j++) {
          mask[i].push(j <= i);
        }
      }
      
      // Apply mask
      const maskedMatrix = matrix.map((row, i) => 
        row.map((val, j) => mask[i][j] ? null : val)
      );
      
      const data = [{
        z: maskedMatrix,
        x: corrColumns,
        y: corrColumns,
        type: 'heatmap',
        colorscale: 'RdBu',
        zmid: 0,
        zmin: -1,
        zmax: 1,
        showscale: true
      }];
      
      const layout = {
        title: {
          text: `<u>${this.getCorrelationTitle(type)}</u>`,
          font: { 
            size: 24,
            color: 'black',
            family: 'Arial, sans-serif'
          }
        },
        width: 1000,
        height: 800,
        paper_bgcolor: 'rgba(0,0,0,0)',
        plot_bgcolor: 'rgba(0,0,0,0)',
        font: { color: 'black', weight: 'bold' },
        xaxis: { showticklabels: false },
        yaxis: { showticklabels: false }
      };
      
      Plotly.newPlot('plotly-chart', data, layout, { responsive: true }).then(() => {
        this.plotInstance = document.getElementById('plotly-chart');
      });
    },
    
    getCorrelationTitle(type) {
      const titles = {
        'correlation_all': 'Feature Correlation Matrix (All Features)',
        'correlation_vegetation': 'Feature Correlation (Vegetation)',
        'correlation_texture': 'Feature Correlation (Texture)',
        'correlation_morphology': 'Feature Correlation (Morphology)'
      };
      return titles[type] || 'Correlation Matrix';
    },
    
    getChartTypeName(chartType) {
      const names = {
        'correlation_all': 'Correlation Heatmap (All)',
        'correlation_vegetation': 'Correlation Heatmap (Vegetation)',
        'correlation_texture': 'Correlation Heatmap (Texture)',
        'correlation_morphology': 'Correlation Heatmap (Morphology)',
        'nested_pie': 'Nested Pie Chart',
        'side_by_side_pie': 'Side-by-Side Pie Charts',
        'violin': 'Violin Plots',
        'boxplot': 'Boxplots',
        'pca_2d': 'PCA 2D',
        'pca_3d': 'PCA 3D',
        'tsne_2d': 't-SNE 2D',
        'tsne_3d': 't-SNE 3D'
      };
      return names[chartType] || chartType;
    },
    
    renderNestedPieChart() {
      // Count mutation groups
      const groupCounts = {};
      this.processedData.forEach(row => {
        if (row.mutation) {
          groupCounts[row.mutation] = (groupCounts[row.mutation] || 0) + 1;
        }
      });
      
      // Count feature categories
      const cleaned = loadAndCleanFeatures(this.processedData);
      const featureGroups = splitFeatureGroups(cleaned.featureColumns);
      const categoryCounts = {
        'Texture': featureGroups.Texture.length,
        'Vegetation': featureGroups.Vegetation.length,
        'Morphology': featureGroups.Morphology.length
      };
      
      const groupLabels = Object.keys(groupCounts);
      const groupValues = Object.values(groupCounts);
      const categoryLabels = Object.keys(categoryCounts);
      const categoryValues = Object.values(categoryCounts);
      
      const palette = {
        'NT': '#4C4C4C',
        'group1': '#1f77b4',
        'group2': '#ff7f0e',
        'group3': '#2ca02c',
        'group4': '#d62728',
        'group5': '#9467bd',
        'group6': '#8c564b',
        'group7': '#e377c2'
      };
      
      const categoryColors = ['#E74C3C', '#27AE60', '#3498DB'];
      
      const outerColors = groupLabels.map(g => palette[g] || '#999999');
      const innerColors = categoryColors.slice(0, categoryLabels.length);
      
      const data = [
        {
          type: 'pie',
          values: groupValues,
          labels: groupLabels,
          domain: { x: [0, 1], y: [0, 1] },
          name: 'Mutation Groups',
          marker: { colors: outerColors },
          hole: 0.4,
          textinfo: 'label+percent',
          textposition: 'outside'
        },
        {
          type: 'pie',
          values: categoryValues,
          labels: categoryLabels,
          domain: { x: [0.2, 0.8], y: [0.2, 0.8] },
          name: 'Feature Categories',
          marker: { colors: innerColors },
          hole: 0.7,
          textinfo: 'label+percent'
        }
      ];
      
      const layout = {
        title: {
          text: '<u>Nested Pie Chart: Mutation Groups & Feature Categories</u>',
          font: { 
            size: 24,
            color: 'black',
            family: 'Arial, sans-serif'
          }
        },
        width: 1000,
        height: 800,
        paper_bgcolor: 'rgba(0,0,0,0)',
        plot_bgcolor: 'rgba(0,0,0,0)',
        font: { color: 'black', weight: 'bold' },
        showlegend: true
      };
      
      Plotly.newPlot('plotly-chart', data, layout, { responsive: true }).then(() => {
        this.plotInstance = document.getElementById('plotly-chart');
      });
    },
    
    renderSideBySidePieCharts() {
      // Mutation groups
      const groupCounts = {};
      this.processedData.forEach(row => {
        if (row.mutation) {
          groupCounts[row.mutation] = (groupCounts[row.mutation] || 0) + 1;
        }
      });
      
      // Feature categories
      const cleaned = loadAndCleanFeatures(this.processedData);
      const featureGroups = splitFeatureGroups(cleaned.featureColumns);
      const categoryCounts = {
        'Texture': featureGroups.Texture.length,
        'Vegetation': featureGroups.Vegetation.length,
        'Morphology': featureGroups.Morphology.length
      };
      
      const palette = {
        'NT': '#4C4C4C',
        'group1': '#1f77b4',
        'group2': '#ff7f0e',
        'group3': '#2ca02c',
        'group4': '#d62728',
        'group5': '#9467bd',
        'group6': '#8c564b',
        'group7': '#e377c2'
      };
      
      const data = [
        {
          type: 'pie',
          values: Object.values(groupCounts),
          labels: Object.keys(groupCounts),
          domain: { x: [0, 0.48], y: [0, 1] },
          name: 'Mutation Groups',
          marker: { colors: Object.keys(groupCounts).map(g => palette[g] || '#999999') },
          textinfo: 'label+percent'
        },
        {
          type: 'pie',
          values: Object.values(categoryCounts),
          labels: Object.keys(categoryCounts),
          domain: { x: [0.52, 1], y: [0, 1] },
          name: 'Feature Categories',
          marker: { colors: ['#E74C3C', '#27AE60', '#3498DB'] },
          textinfo: 'label+percent'
        }
      ];
      
      const layout = {
        title: {
          text: '<u>Side-by-Side Pie Charts</u>',
          font: { 
            size: 24,
            color: 'black',
            family: 'Arial, sans-serif'
          }
        },
        width: 1000,
        height: 800,
        paper_bgcolor: 'rgba(0,0,0,0)',
        plot_bgcolor: 'rgba(0,0,0,0)',
        font: { color: 'black', weight: 'bold' },
        showlegend: true
      };
      
      Plotly.newPlot('plotly-chart', data, layout, { responsive: true }).then(() => {
        this.plotInstance = document.getElementById('plotly-chart');
      });
    },
    
    renderViolinPlots() {
      const cleaned = loadAndCleanFeatures(this.processedData);
      const featureGroups = splitFeatureGroups(cleaned.featureColumns);
      
      // Z-score normalize
      const normalized = zscoreNormalize(cleaned.data, cleaned.featureColumns);
      const normalizedViolinData = prepareViolinData(normalized, featureGroups);
      
      const categories = ['Vegetation', 'Texture', 'Morphology'];
      const order = ['NT', 'group1', 'group2', 'group3', 'group4', 'group5', 'group6', 'group7'];
      const palette = {
        'NT': '#4C4C4C',
        'group1': '#1f77b4',
        'group2': '#ff7f0e',
        'group3': '#2ca02c',
        'group4': '#d62728',
        'group5': '#9467bd',
        'group6': '#8c564b',
        'group7': '#e377c2'
      };
      
      const traces = [];
      categories.forEach((category, catIdx) => {
        const catData = normalizedViolinData.filter(d => d.category === category);
        if (catData.length === 0) return;
        
        order.forEach(group => {
          const groupData = catData.filter(d => d.mutation === group).map(d => d.value);
          if (groupData.length > 0) {
            traces.push({
              type: 'violin',
              y: groupData,
              name: group,
              box: { visible: false },
              meanline: { visible: true },
              x0: category,
              side: 'negative',
              width: 0.6,
              marker: { color: palette[group] || '#999999' },
              legendgroup: group,
              showlegend: catIdx === 0
            });
          }
        });
      });
      
      const layout = {
        title: {
          text: '<u>Feature Distributions by Mutation Group — Multi-Date</u>',
          font: { 
            size: 24,
            color: 'black',
            family: 'Arial, sans-serif'
          }
        },
        width: 1000,
        height: 800,
        paper_bgcolor: 'rgba(0,0,0,0)',
        plot_bgcolor: 'rgba(0,0,0,0)',
        font: { color: 'black', weight: 'bold' },
        xaxis: { title: 'Category' },
        yaxis: { title: 'Z-scored feature values (pooled)' },
        violingap: 0,
        violingroupgap: 0
      };
      
      Plotly.newPlot('plotly-chart', traces, layout, { responsive: true }).then(() => {
        this.plotInstance = document.getElementById('plotly-chart');
      });
    },
    
    renderBoxplots() {
      const features = {
        'green_lac1_mean': 'Texture Lacunarity 1 Mean',
        'ndvi_mean': 'Vegetation NDVI Mean',
        'morph_height': 'Morphology Height (cm)'
      };
      
      const featureKeys = Object.keys(features);
      const boxplotData = prepareBoxplotData(this.processedData, featureKeys);
      
      const order = ['group1', 'group2', 'group3', 'group4', 'group5', 'group6', 'group7', 'NT'];
      const palette = {
        'NT': '#4C4C4C',
        'group1': '#1f77b4',
        'group2': '#ff7f0e',
        'group3': '#2ca02c',
        'group4': '#d62728',
        'group5': '#9467bd',
        'group6': '#8c564b',
        'group7': '#e377c2'
      };
      
      const traces = [];
      featureKeys.forEach((feature, featIdx) => {
        order.forEach(group => {
          const values = boxplotData[feature] && boxplotData[feature][group] ? boxplotData[feature][group] : [];
          if (values.length > 0) {
            traces.push({
              type: 'box',
              y: values,
              name: group,
              x: features[feature],
              marker: { color: palette[group] || '#999999' },
              legendgroup: group,
              showlegend: featIdx === 0
            });
          }
        });
      });
      
      const layout = {
        title: {
          text: '<u>Feature Analysis by Mutation Groups — Multi-Date</u>',
          font: { 
            size: 24,
            color: 'black',
            family: 'Arial, sans-serif'
          }
        },
        width: 1000,
        height: 800,
        paper_bgcolor: 'rgba(0,0,0,0)',
        plot_bgcolor: 'rgba(0,0,0,0)',
        font: { color: 'black', weight: 'bold' },
        xaxis: { title: 'Feature' },
        yaxis: { title: 'Feature Value' },
        boxmode: 'group'
      };
      
      Plotly.newPlot('plotly-chart', traces, layout, { responsive: true }).then(() => {
        this.plotInstance = document.getElementById('plotly-chart');
      });
    },
    
    async renderPCA2D() {
      try {
        const response = await getPCA(2, this.selectedSpecies || null);
        const data = response.data || [];
        const explained = response.explained_variance || [0, 0];
        
        if (data.length === 0) {
          this.errorMessage = 'No data available for PCA computation';
          return;
        }
        
        // Clear any existing chart
        const plotElement = document.getElementById('plotly-chart');
        if (plotElement) {
          Plotly.purge(plotElement);
        }
        
        // Group data by mutation
        const palette = {
          'NT': '#4C4C4C',
          'group1': '#1f77b4',
          'group2': '#ff7f0e',
          'group3': '#2ca02c',
          'group4': '#d62728',
          'group5': '#9467bd',
          'group6': '#8c564b',
          'group7': '#e377c2'
        };
        
        const order = ['NT', 'group1', 'group2', 'group3', 'group4', 'group5', 'group6', 'group7'];
        const traces = [];
        
        order.forEach(mutation => {
          const groupData = data.filter(d => d.mutation === mutation);
          if (groupData.length > 0) {
            traces.push({
              x: groupData.map(d => d.pc1),
              y: groupData.map(d => d.pc2),
              mode: 'markers',
              type: 'scatter',
              name: mutation,
              marker: {
                color: palette[mutation] || '#999999',
                size: 8,
                line: {
                  color: 'black',
                  width: 0.5
                }
              },
              text: groupData.map(d => d.plant),
              hovertemplate: '<b>%{text}</b><br>PC1: %{x:.2f}<br>PC2: %{y:.2f}<extra></extra>'
            });
          }
        });
        
        const layout = {
          title: {
            text: '<u>PCA 2D — Multi-Date</u>',
            font: { 
              size: 24,
              color: 'black',
              family: 'Arial, sans-serif'
            }
          },
          width: 1000,
          height: 800,
          paper_bgcolor: 'rgba(0,0,0,0)',
          plot_bgcolor: 'rgba(0,0,0,0)',
          font: { color: 'black', weight: 'bold' },
          xaxis: {
            title: `PC1 (${(explained[0] * 100).toFixed(1)}%)`,
            showgrid: true,
            gridcolor: 'rgba(0,0,0,0.1)'
          },
          yaxis: {
            title: `PC2 (${(explained[1] * 100).toFixed(1)}%)`,
            showgrid: true,
            gridcolor: 'rgba(0,0,0,0.1)'
          },
          legend: {
            title: { text: 'Mutation Group' },
            x: 1.02,
            y: 0.5
          }
        };
        
        await this.$nextTick();
        Plotly.newPlot('plotly-chart', traces, layout, { responsive: true }).then(() => {
          this.plotInstance = document.getElementById('plotly-chart');
        });
      } catch (error) {
        console.error('Error rendering PCA 2D:', error);
        this.errorMessage = `Error rendering PCA 2D: ${error.message}`;
        throw error;
      }
    },
    
    async renderPCA3D() {
      try {
        const response = await getPCA(3, this.selectedSpecies || null);
        const data = response.data || [];
        const explained = response.explained_variance || [0, 0, 0];
        
        if (data.length === 0) {
          this.errorMessage = 'No data available for PCA computation';
          return;
        }
        
        // Clear any existing chart
        const plotElement = document.getElementById('plotly-chart');
        if (plotElement) {
          Plotly.purge(plotElement);
        }
        
        // Group data by mutation
        const palette = {
          'NT': '#4C4C4C',
          'group1': '#1f77b4',
          'group2': '#ff7f0e',
          'group3': '#2ca02c',
          'group4': '#d62728',
          'group5': '#9467bd',
          'group6': '#8c564b',
          'group7': '#e377c2'
        };
        
        const order = ['NT', 'group1', 'group2', 'group3', 'group4', 'group5', 'group6', 'group7'];
        const traces = [];
        
        order.forEach(mutation => {
          const groupData = data.filter(d => d.mutation === mutation);
          if (groupData.length > 0) {
            traces.push({
              x: groupData.map(d => d.pc1),
              y: groupData.map(d => d.pc2),
              z: groupData.map(d => d.pc3),
              mode: 'markers',
              type: 'scatter3d',
              name: mutation,
              marker: {
                color: palette[mutation] || '#999999',
                size: 5,
                line: {
                  color: 'black',
                  width: 0.3
                }
              },
              text: groupData.map(d => d.plant),
              hovertemplate: '<b>%{text}</b><br>PC1: %{x:.2f}<br>PC2: %{y:.2f}<br>PC3: %{z:.2f}<extra></extra>'
            });
          }
        });
        
        const layout = {
          title: {
            text: '<u>PCA 3D — Multi-Date</u>',
            font: { 
              size: 24,
              color: 'black',
              family: 'Arial, sans-serif'
            }
          },
          width: 1000,
          height: 800,
          paper_bgcolor: 'rgba(0,0,0,0)',
          plot_bgcolor: 'rgba(0,0,0,0)',
          font: { color: 'black', weight: 'bold' },
          scene: {
            xaxis: { title: `PC1 (${(explained[0] * 100).toFixed(1)}%)` },
            yaxis: { title: `PC2 (${(explained[1] * 100).toFixed(1)}%)` },
            zaxis: { title: `PC3 (${(explained[2] * 100).toFixed(1)}%)` }
          },
          legend: {
            title: { text: 'Mutation Group' },
            x: 1.02,
            y: 0.5
          }
        };
        
        await this.$nextTick();
        Plotly.newPlot('plotly-chart', traces, layout, { responsive: true }).then(() => {
          this.plotInstance = document.getElementById('plotly-chart');
        });
      } catch (error) {
        console.error('Error rendering PCA 3D:', error);
        this.errorMessage = `Error rendering PCA 3D: ${error.message}`;
        throw error;
      }
    },
    
    async renderTSNE2D() {
      try {
        const response = await getTSNE(2, this.selectedSpecies || null);
        const data = response.data || [];
        
        if (data.length === 0) {
          this.errorMessage = 'No data available for t-SNE computation';
          return;
        }
        
        // Clear any existing chart
        const plotElement = document.getElementById('plotly-chart');
        if (plotElement) {
          Plotly.purge(plotElement);
        }
        
        // Group data by mutation
        const palette = {
          'NT': '#4C4C4C',
          'group1': '#1f77b4',
          'group2': '#ff7f0e',
          'group3': '#2ca02c',
          'group4': '#d62728',
          'group5': '#9467bd',
          'group6': '#8c564b',
          'group7': '#e377c2'
        };
        
        const order = ['NT', 'group1', 'group2', 'group3', 'group4', 'group5', 'group6', 'group7'];
        const traces = [];
        
        order.forEach(mutation => {
          const groupData = data.filter(d => d.mutation === mutation);
          if (groupData.length > 0) {
            traces.push({
              x: groupData.map(d => d.tsne1),
              y: groupData.map(d => d.tsne2),
              mode: 'markers',
              type: 'scatter',
              name: mutation,
              marker: {
                color: palette[mutation] || '#999999',
                size: 8,
                line: {
                  color: 'black',
                  width: 0.5
                }
              },
              text: groupData.map(d => d.plant),
              hovertemplate: '<b>%{text}</b><br>t-SNE 1: %{x:.2f}<br>t-SNE 2: %{y:.2f}<extra></extra>'
            });
          }
        });
        
        const layout = {
          title: {
            text: '<u>t-SNE 2D — Multi-Date</u>',
            font: { 
              size: 24,
              color: 'black',
              family: 'Arial, sans-serif'
            }
          },
          width: 1000,
          height: 800,
          paper_bgcolor: 'rgba(0,0,0,0)',
          plot_bgcolor: 'rgba(0,0,0,0)',
          font: { color: 'black', weight: 'bold' },
          xaxis: {
            title: 't-SNE 1',
            showgrid: true,
            gridcolor: 'rgba(0,0,0,0.1)'
          },
          yaxis: {
            title: 't-SNE 2',
            showgrid: true,
            gridcolor: 'rgba(0,0,0,0.1)'
          },
          legend: {
            title: { text: 'Mutation Group' },
            x: 1.02,
            y: 0.5
          }
        };
        
        await this.$nextTick();
        Plotly.newPlot('plotly-chart', traces, layout, { responsive: true }).then(() => {
          this.plotInstance = document.getElementById('plotly-chart');
        });
      } catch (error) {
        console.error('Error rendering t-SNE 2D:', error);
        this.errorMessage = `Error rendering t-SNE 2D: ${error.message}`;
        throw error;
      }
    },
    
    async renderTSNE3D() {
      try {
        const response = await getTSNE(3, this.selectedSpecies || null);
        const data = response.data || [];
        
        if (data.length === 0) {
          this.errorMessage = 'No data available for t-SNE computation';
          return;
        }
        
        // Clear any existing chart
        const plotElement = document.getElementById('plotly-chart');
        if (plotElement) {
          Plotly.purge(plotElement);
        }
        
        // Group data by mutation
        const palette = {
          'NT': '#4C4C4C',
          'group1': '#1f77b4',
          'group2': '#ff7f0e',
          'group3': '#2ca02c',
          'group4': '#d62728',
          'group5': '#9467bd',
          'group6': '#8c564b',
          'group7': '#e377c2'
        };
        
        const order = ['NT', 'group1', 'group2', 'group3', 'group4', 'group5', 'group6', 'group7'];
        const traces = [];
        
        order.forEach(mutation => {
          const groupData = data.filter(d => d.mutation === mutation);
          if (groupData.length > 0) {
            traces.push({
              x: groupData.map(d => d.tsne1),
              y: groupData.map(d => d.tsne2),
              z: groupData.map(d => d.tsne3),
              mode: 'markers',
              type: 'scatter3d',
              name: mutation,
              marker: {
                color: palette[mutation] || '#999999',
                size: 5,
                line: {
                  color: 'black',
                  width: 0.3
                }
              },
              text: groupData.map(d => d.plant),
              hovertemplate: '<b>%{text}</b><br>t-SNE 1: %{x:.2f}<br>t-SNE 2: %{y:.2f}<br>t-SNE 3: %{z:.2f}<extra></extra>'
            });
          }
        });
        
        const layout = {
          title: {
            text: '<u>t-SNE 3D — Multi-Date</u>',
            font: { 
              size: 24,
              color: 'black',
              family: 'Arial, sans-serif'
            }
          },
          width: 1000,
          height: 800,
          paper_bgcolor: 'rgba(0,0,0,0)',
          plot_bgcolor: 'rgba(0,0,0,0)',
          font: { color: 'black', weight: 'bold' },
          scene: {
            xaxis: { title: 't-SNE 1' },
            yaxis: { title: 't-SNE 2' },
            zaxis: { title: 't-SNE 3' }
          },
          legend: {
            title: { text: 'Mutation Group' },
            x: 1.02,
            y: 0.5
          }
        };
        
        await this.$nextTick();
        Plotly.newPlot('plotly-chart', traces, layout, { responsive: true }).then(() => {
          this.plotInstance = document.getElementById('plotly-chart');
        });
      } catch (error) {
        console.error('Error rendering t-SNE 3D:', error);
        this.errorMessage = `Error rendering t-SNE 3D: ${error.message}`;
        throw error;
      }
    }
  }
};
</script>

<style scoped>
.charts-view {
  width: 100%;
  height: 100%;
  padding: 20px;
}

.charts-layout {
  display: grid;
  grid-template-columns: 1fr 400px;
  gap: 20px;
  height: 100%;
}

.plot-space {
  position: relative;
  background: rgba(255, 255, 255, 0.08);
  border-radius: 12px;
  padding: 25px;
  min-height: 700px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.plot-placeholder {
  text-align: center;
  color: rgba(0, 0, 0, 0.7);
  font-size: 18px;
  font-weight: 900;
}

.download-section {
  margin-top: 50px;
  margin-bottom: 20px;
}

.download-button {
  width: 100%;
  padding: 15px 25px;
  background: #4ade80;
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}

.download-button:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 12px rgba(74, 222, 128, 0.3);
  background: #22c55e;
}

.download-button:active {
  transform: translateY(0);
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  background: #16a34a;
}

.plotly-container {
  width: 100%;
  height: 100%;
}

.selection-pane {
  background: rgba(255, 255, 255, 0.1);
  border-radius: 12px;
  padding: 20px;
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.2);
  height: 50%;
  margin-top: 150px;
  margin-right: 20px;
}

.pane-title {
  color: white;
  font-size: 20px;
  font-weight: 600;
  margin-bottom: 20px;
  text-align: center;
  text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.5);
}

.species-selector {
  margin-bottom: 20px;
}

.chart-type-selector {
  margin-bottom: 20px;
}

.selector-label {
  display: block;
  color: rgb(0, 0, 0);
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 8px;
}

.chart-select {
  width: 100%;
  padding: 10px;
  border: 1px solid rgba(255, 255, 255, 0.3);
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.1);
  color: rgb(0, 0, 0);
  font-size: 14px;
  cursor: pointer;
}

.chart-select:focus {
  outline: none;
  border-color: #4ade80;
  background: rgba(255, 255, 255, 0.15);
}

.chart-select option {
  background: #333;
  color: rgb(0, 0, 0);
}

.loading-message,
.error-message {
  padding: 10px;
  border-radius: 6px;
  margin-top: 20px;
  text-align: center;
}

.loading-message {
  background: rgba(74, 222, 128, 0.2);
  color: #4ade80;
  color: white;
}

.error-message {
  background: rgba(251, 191, 36, 0.2);
  color: #fbbf24;
  color: white;
}

.loading-message p,
.error-message p {
  margin: 0;
  font-size: 14px;
}

.loading-overlay {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-color: rgba(255, 255, 255, 0.04);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 10;
  border-radius: 12px;
}

.loading-indicator-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 20px;
}

.loading-text {
  color: rgba(0, 0, 0, 0.7);
  font-size: 18px;
  font-weight: 900;
  margin: 0;
}

/* Loading animation - 3x3 grid of dots */
.loader {
  width: 4px;
  color: #000;
  aspect-ratio: 1;
  border-radius: 50%;
  box-shadow: 
    19px -19px 0 0px, 38px -19px 0 0px, 57px -19px 0 0px,
    19px 0     0 5px, 38px 0     0 5px, 57px 0     0 5px,
    19px 19px  0 0px, 38px 19px  0 0px, 57px 19px  0 0px;
  transform: translateX(-38px);
  animation: l26 2s infinite linear;
}

@keyframes l26 {
  12.5% {box-shadow: 
    19px -19px 0 0px, 38px -19px 0 0px, 57px -19px 0 5px,
    19px 0     0 5px, 38px 0     0 0px, 57px 0     0 5px,
    19px 19px  0 0px, 38px 19px  0 0px, 57px 19px  0 0px}
  25%   {box-shadow: 
    19px -19px 0 5px, 38px -19px 0 0px, 57px -19px 0 5px,
    19px 0     0 0px, 38px 0     0 0px, 57px 0     0 0px,
    19px 19px  0 0px, 38px 19px  0 5px, 57px 19px  0 0px}
  50%   {box-shadow: 
    19px -19px 0 5px, 38px -19px 0 5px, 57px -19px 0 0px,
    19px 0     0 0px, 38px 0     0 0px, 57px 0     0 0px,
    19px 19px  0 0px, 38px 19px  0 0px, 57px 19px  0 5px}
  62.5% {box-shadow: 
    19px -19px 0 0px, 38px -19px 0 0px, 57px -19px 0 0px,
    19px 0     0 5px, 38px 0     0 0px, 57px 0     0 0px,
    19px 19px  0 0px, 38px 19px  0 5px, 57px 19px  0 5px}
  75%   {box-shadow: 
    19px -19px 0 0px, 38px -19px 0 5px, 57px -19px 0 0px,
    19px 0     0 0px, 38px 0     0 0px, 57px 0     0 5px,
    19px 19px  0 0px, 38px 19px  0 0px, 57px 19px  0 5px}
  87.5% {box-shadow: 
    19px -19px 0 0px, 38px -19px 0 5px, 57px -19px 0 0px,
    19px 0     0 0px, 38px 0     0 5px, 57px 0     0 0px,
    19px 19px  0 5px, 38px 19px  0 0px, 57px 19px  0 0px}
}
</style>


