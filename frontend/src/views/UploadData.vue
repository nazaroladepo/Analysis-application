<template>
  <div id="upload-data">
    <!-- Background layers -->
    <div class="background-container">
      <!-- Background image layer -->
      <div
        class="background-image"
        :style="backgroundImageStyle"
        v-if="backgroundImage"
      ></div>

      <!-- Gradient overlay -->
      <div
        class="gradient-overlay"
        :style="gradientStyle"
      ></div>
    </div>

    <!-- Content -->
    <div class="app-content">
      <AppHeader :whiteBars="[
        { width: 2216, height: 16, x: -10, y: 175, opacity: 0.8 }]"
      />

      <main class="content">
        <div class="title-container">
          <h1 class="title">Upload Data</h1>
          <div class="back-button" @click="goBack" >
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M19 12H5" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
              <path d="M12 19L5 12L12 5" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
            <div class="tooltip">Back </div>
          </div>
        </div>
        
        <div class="description">
          Upload your plant images for analysis with our advanced AI-powered tools.
        </div>

        <!-- Main Content Grid: Rules on Left, Upload on Right -->
        <div class="main-content-grid">
          <!-- Left Column: Upload Rules -->
          <div class="rules-panel">
            <div class="rules-header">
              <div class="rules-icon">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <path d="M12 2L2 7L12 12L22 7L12 2Z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                  <path d="M2 17L12 22L22 17" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                  <path d="M2 12L12 17L22 12" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
              </div>
              <h3 class="rules-title">File Naming Rules</h3>
            </div>
            <div class="rules-content">
              <!-- Raw Data Rules -->
              <div class="rules-section">
                <div class="rules-section-header">
                  <h4 class="rules-section-title">Raw Dataset Files</h4>
                  <div class="rules-badge">Required</div>
                </div>
                <div class="rules-detail">
                  <p class="rules-label">Directory Structure:</p>
                  <code class="rules-code">{Species}_dataset</code>
                </div>
                <div class="rules-detail">
                  <p class="rules-label">File Format:</p>
                  <code class="rules-code">{Species}_{Date}_plant#.tiff</code>
                </div>
                <div class="rules-example-box">
                  <p class="rules-example-label">Example:</p>
                  <code class="rules-example-code">Sorghum_2024-12-04_plant1.tiff</code>
                </div>
                <ul class="rules-list">
                  <li>
                    <span class="list-icon">✓</span>
                    <span>Species: Capitalize first letter (e.g., Sorghum, Corn, Cotton)</span>
                  </li>
                  <li>
                    <span class="list-icon">✓</span>
                    <span>Date: Format as YYYY-MM-DD (e.g., 2024-12-04)</span>
                  </li>
                  <li>
                    <span class="list-icon">✓</span>
                    <span>Plant number: Use lowercase 'plant' followed by a number (e.g., plant1, plant2)</span>
                  </li>
                  <li>
                    <span class="list-icon">✓</span>
                    <span>File extension: Must be .tiff or .tif</span>
                  </li>
                </ul>
              </div>

              <!-- Processed Data Rules -->
              <div class="rules-section">
                <div class="rules-section-header">
                  <h4 class="rules-section-title">Processed Data Files</h4>
                  <div class="rules-badge optional">Optional</div>
                </div>
                <div class="rules-detail">
                  <p class="rules-label">Directory Structure:</p>
                  <code class="rules-code">{Species}_results</code>
                </div>
                <p class="rules-note">Results should be organized under <code class="rules-code-inline">{Species}_results</code> directory</p>
              </div>
            </div>
          </div>

          <!-- Right Column: Segmentation & Upload -->
          <div class="upload-panel">
            <!-- Segmentation Method Selection -->
            <div v-if="!uploadSuccess && !isUploading" class="segmentation-selector-card">
              <div class="selector-header">
                <div class="selector-icon">
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <path d="M12 2L2 7L12 12L22 7L12 2Z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                    <path d="M2 17L12 22L22 17" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                    <path d="M2 12L12 17L22 12" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                  </svg>
                </div>
                <label class="selector-label">Segmentation Method</label>
              </div>
              <select v-model="segmentationMethod" class="method-select">
                <option value="sam3">SAM3 (Default)</option>
                <option value="rmbg">RMBG-2.0</option>
              </select>
              <div class="method-info">
                <div class="method-info-item">
                  <span class="method-info-badge sam3">SAM3</span>
                  <span class="method-info-text">Advanced segmentation with text prompts (recommended for sorghum plants)</span>
                </div>
                <div class="method-info-item">
                  <span class="method-info-badge rmbg">RMBG-2.0</span>
                  <span class="method-info-text">Legacy background removal method</span>
                </div>
              </div>
            </div>
            
            <!-- Upload Area -->
            <div v-if="!uploadSuccess && !uploadFailed" class="upload-area" 
               @drop="handleDrop" 
               @dragover.prevent 
               @dragenter.prevent
               :class="{ 'dragging': isDragging, 'uploading': isUploading }">
            <div v-if="!isUploading" class="upload-content">
              <div class="upload-icon">
                <svg width="64" height="64" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <path d="M21 15V19C21 19.5304 20.7893 20.0391 20.4142 20.4142C20.0391 20.7893 19.5304 21 19 21H5C4.46957 21 3.96086 20.7893 3.58579 20.4142C3.21071 20.0391 3 19.5304 3 19V15" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                  <path d="M17 8L12 3L7 8" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                  <path d="M12 3V15" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
              </div>
              <h3 class="upload-title">Drag and drop your files here</h3>
              <p class="upload-subtitle">or click to browse</p>
              <input 
                type="file" 
                ref="fileInput" 
                @change="handleFileSelect" 
                multiple 
                accept=".tiff,.tif,image/*"
                class="file-input"
                :disabled="isUploading"
              />
              <button class="browse-button" @click="$refs.fileInput.click()" :disabled="isUploading">
                Browse Files
              </button>
            </div>
            <div v-else class="upload-progress">
              <div class="progress-spinner"></div>
              <p class="progress-text">{{ currentStageText }}</p>
              <div class="progress-bar">
                <div class="progress-fill" :style="{ width: uploadProgress + '%' }"></div>
              </div>
              <p class="progress-percentage">{{ Math.round(uploadProgress) }}%</p>
              <p v-if="currentStage !== 'complete'" class="progress-stage">{{ currentStageDetail }}</p>
            </div>
          </div>

          <!-- Selected Files Display -->
          <div v-if="selectedFiles.length > 0 && !isUploading && !uploadSuccess && !uploadFailed" class="selected-files">
            <h4 class="selected-title">Selected Files ({{ selectedFiles.length }})</h4>
            <div class="files-list">
              <div v-for="(file, index) in selectedFiles" :key="index" class="file-item" 
                   :class="{ 'invalid': !file.isValid }">
                <span class="file-name">{{ file.name }}</span>
                <span v-if="file.isValid" class="file-status valid">✓ Valid</span>
                <span v-else class="file-status invalid">✗ Invalid: {{ file.error }}</span>
              </div>
            </div>
            <div class="upload-actions">
              <button class="upload-btn" @click="uploadFiles" :disabled="!canUpload">
                Upload Files
              </button>
              <button class="clear-btn" @click="clearFiles">Clear Selection</button>
            </div>
          </div>

          <!-- Error Messages -->
          <div v-if="errorMessage" class="error-message">
            <p>{{ errorMessage }}</p>
            <button @click="errorMessage = ''" class="close-error">×</button>
          </div>

          <!-- Failure Page -->
          <div v-if="uploadFailed" class="failure-page">
            <div class="failure-icon">
              <svg width="100" height="100" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <circle cx="12" cy="12" r="10" stroke="#ef4444" stroke-width="3"/>
                <path d="M15 9L9 15M9 9L15 15" stroke="#ef4444" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
            </div>
            <h2 class="failure-title">Upload Failed</h2>
            <p class="failure-message">{{ uploadResult.message || 'The image analysis failed. Please check your file and try again.' }}</p>
            <div class="failure-details">
              <p><strong>Files Uploaded:</strong> {{ uploadResult.files_uploaded || 0 }} of {{ uploadResult.total_files || 0 }}</p>
              <p><strong>Files Processed:</strong> {{ uploadResult.files_processed || 0 }} of {{ uploadResult.files_uploaded || 0 }}</p>
              <p v-if="uploadResult.files_failed_processing > 0" class="error-text">
                <strong>Analysis Failed:</strong> {{ uploadResult.files_failed_processing }} file(s) could not be analyzed
              </p>
              <p class="error-note">The file(s) have been removed from storage due to analysis failure.</p>
            </div>
            <div class="failure-actions">
              <button class="upload-another-btn" @click="resetUpload">
                Try Again
              </button>
              <button class="back-btn" @click="goBack">
                Back to Home
              </button>
            </div>
          </div>

          <!-- Success Page -->
          <div v-else-if="uploadSuccess" class="success-page">
            <div class="success-icon">
              <svg width="80" height="80" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M20 6L9 17L4 12" stroke="#4ade80" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
            </div>
            <h2 class="success-title">Upload and Analysis Complete!</h2>
            <p class="success-message">{{ uploadResult.message || 'All files have been uploaded and analyzed successfully.' }}</p>
            <div class="success-details">
              <p><strong>Files Uploaded:</strong> {{ uploadResult.files_uploaded || 0 }} of {{ uploadResult.total_files || 0 }}</p>
              <p><strong>Files Processed:</strong> {{ uploadResult.files_processed || 0 }} of {{ uploadResult.files_uploaded || 0 }}</p>
              <p v-if="uploadResult.files_failed_upload > 0" class="warning-text">
                <strong>Upload Failed:</strong> {{ uploadResult.files_failed_upload }} file(s)
              </p>
              <p v-if="uploadResult.files_failed_processing > 0" class="warning-text">
                <strong>Analysis Failed:</strong> {{ uploadResult.files_failed_processing }} file(s)
              </p>
              <p v-if="uploadResult.uploaded_files && uploadResult.uploaded_files.length > 0">
                <strong>Results saved to:</strong> S3 crop-specific results folder
              </p>
            </div>
            <div class="success-actions">
              <button v-if="canViewAnalysis" class="view-analysis-btn" @click="viewAnalysis">
                View Analysis
              </button>
              <button class="upload-another-btn" @click="resetUpload">
                Upload Another File
              </button>
              <button class="back-btn" @click="goBack">
                Back to Home
              </button>
            </div>
          </div>
          </div>
        </div>
      </main>
    </div>
  </div>
</template>

<script>
import AppHeader from '../components/AppHeader.vue'
import backgroundImage from '@/assets/greenhouse-img2.jpg'
import { uploadFiles } from '@/api.js'

export default {
  name: 'UploadData',
  components: {
    AppHeader
  },
  data() {
    return {
      // Background configuration
      backgroundImage: backgroundImage,
      backgroundImageOpacity: 0.8,
      
      // Gradient configuration
      gradientTopColor: '#08B6E0',
      gradientBottomColor: '#05AF6B',
      gradientOpacity: 0.7,

      // Upload state
      selectedFiles: [],
      isDragging: false,
      isUploading: false,
      uploadProgress: 0,
      uploadSuccess: false,
      uploadFailed: false,
      uploadResult: null,
      errorMessage: '',
      currentStage: 'upload', // 'upload', 'processing', 'saving', 'complete'
      currentStageDetail: '',
      segmentationMethod: 'sam3', // Default segmentation method
    };
  },
  computed: {
    backgroundImageStyle() {
      if (!this.backgroundImage) return {};
      
      return {
        backgroundImage: `url(${this.backgroundImage})`,
        opacity: this.backgroundImageOpacity
      };
    },
    
    gradientStyle() {
      const topColor = this.hexToRgba(this.gradientTopColor, this.gradientOpacity);
      const bottomColor = this.hexToRgba(this.gradientBottomColor, this.gradientOpacity);
      
      return {
        background: `linear-gradient(to bottom, ${topColor}, ${bottomColor})`
      };
    },
    
    canUpload() {
      return this.selectedFiles.length > 0 && 
             this.selectedFiles.every(f => f.isValid) &&
             !this.isUploading;
    },
    
    canViewAnalysis() {
      // Can view analysis if we have at least one successfully processed file
      return this.uploadSuccess && !this.uploadFailed && 
             this.uploadResult && 
             this.uploadResult.files_processed > 0 &&
             this.selectedFiles.length > 0 &&
             this.selectedFiles[0].isValid &&
             this.selectedFiles[0].species &&
             this.selectedFiles[0].date &&
             this.selectedFiles[0].plantNum;
    },
    
    currentStageText() {
      switch(this.currentStage) {
        case 'upload':
          return `Uploading ${this.selectedFiles.length} file(s) to AWS...`;
        case 'processing':
          return `Analyzing ${this.selectedFiles.length} file(s)...`;
        case 'saving':
          return `Saving results to database...`;
        case 'complete':
          return 'Upload and Analysis Complete!';
        default:
          return 'Processing...';
      }
    }
  },
  methods: {
    goBack() {
      this.$router.push({ name: 'HomePage' });
    },
    
    validateFileName(filename) {
      // Pattern: {Species}_{Date}_plant#.tiff
      // Example: Sorghum_2024-12-04_plant1.tiff
      // Species may be hyphenated, e.g. "Mullet-sorghum"
      const pattern = /^([A-Z][A-Za-z-]+)_(\d{4}-\d{2}-\d{2})_plant(\d+)\.(tiff|tif)$/i;
      const match = filename.match(pattern);
      
      if (!match) {
        return {
          isValid: false,
          error: 'Filename must match format: {Species}_{Date}_plant#.tiff'
        };
      }

      const [, species, date, plantNum] = match;
      
      // Validate date format
      const dateObj = new Date(date);
      if (isNaN(dateObj.getTime())) {
        return {
          isValid: false,
          error: 'Invalid date format. Use YYYY-MM-DD'
        };
      }

      // Validate species (should start with capital)
      if (species[0] !== species[0].toUpperCase()) {
        return {
          isValid: false,
          error: 'Species must start with capital letter'
        };
      }

      return {
        isValid: true,
        species,
        date,
        plantNum
      };
    },

    handleFileSelect(event) {
      const files = Array.from(event.target.files);
      this.processFiles(files);
    },

    handleDrop(event) {
      event.preventDefault();
      this.isDragging = false;
      const files = Array.from(event.dataTransfer.files);
      this.processFiles(files);
    },

    processFiles(files) {
      this.errorMessage = '';
      this.selectedFiles = files.map(file => {
        const validation = this.validateFileName(file.name);
        return {
          file: file, // Keep reference to original File object
          name: file.name,
          size: file.size,
          ...validation
        };
      });

      // Show error if any files are invalid
      const invalidFiles = this.selectedFiles.filter(f => !f.isValid);
      if (invalidFiles.length > 0) {
        this.errorMessage = `Some files have invalid names. Please check the naming rules above.`;
      }
    },

    clearFiles() {
      this.selectedFiles = [];
      this.errorMessage = '';
      if (this.$refs.fileInput) {
        this.$refs.fileInput.value = '';
      }
    },

    async uploadFiles() {
      if (!this.canUpload) {
        return;
      }

      this.isUploading = true;
      this.uploadProgress = 0;
      this.errorMessage = '';
      this.currentStage = 'upload';
      this.currentStageDetail = '';

      try {
        // Extract the original File objects from selectedFiles
        const fileArray = this.selectedFiles.map(f => f.file);
        
        // Stage 1: Upload progress (0-30%)
        this.currentStage = 'upload';
        this.currentStageDetail = 'Uploading files to AWS S3...';
        const uploadProgressInterval = setInterval(() => {
          if (this.uploadProgress < 30) {
            this.uploadProgress += 2;
          }
        }, 100);

        // Stage 2: Processing progress (30-90%)
        setTimeout(() => {
          clearInterval(uploadProgressInterval);
          this.currentStage = 'processing';
          this.currentStageDetail = 'Running analysis pipeline (this may take a few minutes)...';
          
          const processingProgressInterval = setInterval(() => {
            if (this.uploadProgress < 90) {
              this.uploadProgress += 1;
            }
          }, 500);
          
          // Clear this interval when we get the response
          this._processingInterval = processingProgressInterval;
        }, 2000);

        const result = await uploadFiles(fileArray, 'raw-files', this.segmentationMethod);
        
        // Clear any intervals
        if (this._processingInterval) {
          clearInterval(this._processingInterval);
        }
        
        // Stage 3: Saving progress (90-100%)
        this.currentStage = 'saving';
        this.currentStageDetail = 'Saving results to database...';
        this.uploadProgress = 95;
        
        // Wait a moment for progress to show
        await new Promise(resolve => setTimeout(resolve, 500));
        
        // Check results
        const filesUploaded = result.files_uploaded || 0;
        const filesFailed = result.files_failed_upload || 0;
        const filesFailedProcessing = result.files_failed_processing || 0;
        const filesProcessed = result.files_processed || 0;
        
        if (filesUploaded === 0) {
          // No files were uploaded - show error
          this.isUploading = false;
          this.uploadProgress = 0;
          this.currentStage = 'upload';
          this.errorMessage = result.detail || result.message || 'Failed to upload files to AWS. Please check your credentials and try again.';
          throw new Error(this.errorMessage);
        }
        
        // Check if all files failed processing
        if (filesProcessed === 0 && filesUploaded > 0) {
          // All files failed analysis - show failure page
          this.uploadProgress = 100;
          this.currentStage = 'complete';
          this.currentStageDetail = '';
          
          await new Promise(resolve => setTimeout(resolve, 1000));
          
          this.uploadResult = result;
          this.uploadFailed = true;
          this.uploadSuccess = false;
          this.isUploading = false;
          return;
        }
        
        // Stage 4: Complete
        this.uploadProgress = 100;
        this.currentStage = 'complete';
        this.currentStageDetail = '';
        
        await new Promise(resolve => setTimeout(resolve, 1000));
        
        // Some or all files processed successfully
        this.uploadResult = result;
        this.uploadSuccess = true;
        this.uploadFailed = false;
        this.isUploading = false;
        
        // Show warnings if any failures
        if (filesFailed > 0 || filesFailedProcessing > 0) {
          let warningMsg = '';
          if (filesFailed > 0) {
            warningMsg += `${filesFailed} file(s) failed to upload. `;
          }
          if (filesFailedProcessing > 0) {
            warningMsg += `${filesFailedProcessing} file(s) failed during analysis.`;
          }
          this.errorMessage = `Warning: ${warningMsg}`;
        }
        
      } catch (error) {
        this.isUploading = false;
        this.uploadProgress = 0;
        this.currentStage = 'upload';
        this.errorMessage = error.message || 'Upload failed. Please try again.';
        console.error('Upload error:', error);
      }
    },

    resetUpload() {
      this.uploadSuccess = false;
      this.uploadFailed = false;
      this.uploadResult = null;
      this.selectedFiles = [];
      this.uploadProgress = 0;
      this.errorMessage = '';
      this.currentStage = 'upload';
      this.currentStageDetail = '';
      if (this.$refs.fileInput) {
        this.$refs.fileInput.value = '';
      }
    },
    
    viewAnalysis() {
      if (!this.canViewAnalysis) {
        return;
      }
      
      // Get the first successfully uploaded file
      const firstFile = this.selectedFiles.find(f => f.isValid) || this.selectedFiles[0];
      
      if (!firstFile || !firstFile.species || !firstFile.date || !firstFile.plantNum) {
        console.error('Cannot view analysis: missing file information');
        return;
      }
      
      // Use the crop/species parsed from the filename so the user lands
      // on the actual crop page instead of the generic "Uploaded" species
      const species = firstFile.species;           // e.g. "Sorghum" or "Mullet-sorghum"
      const plantId = `plant${firstFile.plantNum}`;
      const date = firstFile.date;
      
      // Debug logging: verify we are using the species parsed from the actual file name
      console.log('[UploadData] View Analysis - selected file:', {
        originalFileName: firstFile.name,
        parsedSpecies: species,
        parsedDate: date,
        parsedPlantNum: firstFile.plantNum
      });
      
      // Navigate to PlantDetails page for this crop
      this.$router.push({
        name: 'PlantDetails',
        params: {
          speciesName: species
        },
        query: {
          plantId: plantId,
          date: date
        }
      });
    },
    
    // Helper method to convert hex color to rgba with opacity
    hexToRgba(hex, opacity) {
      const r = parseInt(hex.slice(1, 3), 16);
      const g = parseInt(hex.slice(3, 5), 16);
      const b = parseInt(hex.slice(5, 7), 16);
      return `rgba(${r}, ${g}, ${b}, ${opacity})`;
    }
  }
}
</script>

<style>
/* Global styles - allow scrolling for upload page */
html, body {
  overflow: auto;
  margin: 0;
  padding: 0;
  height: 100%;
  width: 100%;
}

/* Styled scrollbars for webkit browsers */
::-webkit-scrollbar {
  width: 10px;
}

::-webkit-scrollbar-track {
  background: rgba(0, 0, 0, 0.1);
}

::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.3);
  border-radius: 5px;
}

::-webkit-scrollbar-thumb:hover {
  background: rgba(255, 255, 255, 0.5);
}

/* Styled scrollbars for Firefox */
html {
  scrollbar-width: thin;
  scrollbar-color: rgba(255, 255, 255, 0.3) rgba(0, 0, 0, 0.1);
}
</style>

<style scoped>
#upload-data {
  font-family: Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  position: relative;
  min-height: 100vh;
  width: 100vw;
  overflow-y: auto;
  overflow-x: hidden;
}

/* Background container that covers the entire screen */
.background-container {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  z-index: -1;
}

/* Background image layer */
.background-image {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-size: cover;
  background-position: center;
  background-repeat: no-repeat;
  background-attachment: fixed;
}

/* Disable fixed attachment on mobile for better performance */
@media (max-width: 768px) {
  .background-image {
    background-attachment: scroll;
  }
}

/* Gradient overlay */
.gradient-overlay {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
}

/* Content container */
.app-content {
  position: relative;
  z-index: 1;
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: flex-start;
  padding: 20px;
  text-align: center;
  padding-bottom: 60px;
  padding-top: 200px; /* Space for header */
}

.content {
  width: 100%;
  max-width: 1200px;
  margin: 0 auto;
}

.title-container {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 20px;
  margin-top: 0;
  margin-bottom: 20px;
}

.title {
  color: white;
  font-size: 73px;
  margin-top: 10px;
  margin-bottom: 0px;
  text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.5);
  font-weight: 900;
}

.back-button {
  position: fixed;
  top: 220px;
  left: 40px;
  cursor: pointer;
  padding: 8px;
  border-radius: 50%;
  transition: all 0.3s ease;
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(10px);
  z-index: 5; /* Above header */
}

.back-button:hover {
  background: rgba(255, 255, 255, 0.2);
  transform: scale(1.1);
}

.back-button svg {
  display: block;
  filter: drop-shadow(0 2px 4px rgba(0, 0, 0, 0.3));
}

.tooltip {
  position: absolute;
  bottom: -40px;
  left: 50%;
  transform: translateX(-50%);
  background: rgba(0, 0, 0, 0.8);
  color: white;
  padding: 6px 12px;
  border-radius: 6px;
  font-size: 14px;
  white-space: nowrap;
  opacity: 0;
  visibility: hidden;
  transition: all 0.3s ease;
  pointer-events: none;
  backdrop-filter: blur(10px);
}

.back-button:hover .tooltip {
  opacity: 1;
  visibility: visible;
  bottom: -35px;
}

.description {
  color: white;
  font-size: 20px;
  max-width: 450px;
  margin: 0 auto 40px auto;
  text-shadow: 1px 1px 2px rgb(0, 0, 0);
  line-height: 1.6;
  opacity: 0.9;
}

/* Main Content Grid: Two Column Layout */
.main-content-grid {
  display: grid;
  grid-template-columns: 1fr 1.2fr;
  gap: 32px;
  margin-top: 40px;
  max-width: 1400px;
  margin-left: auto;
  margin-right: auto;
  align-items: start;
}

/* Left Column: Rules Panel */
.rules-panel {
  background: rgba(255, 255, 255, 0.12);
  backdrop-filter: blur(20px);
  border-radius: 20px;
  padding: 32px;
  border: 1px solid rgba(255, 255, 255, 0.2);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
  position: sticky;
  top: 220px; /* Below header area */
  max-height: calc(100vh - 240px);
  overflow-y: auto;
}

/* Custom scrollbar for rules panel */
.rules-panel::-webkit-scrollbar {
  width: 8px;
}

.rules-panel::-webkit-scrollbar-track {
  background: rgba(255, 255, 255, 0.05);
  border-radius: 4px;
}

.rules-panel::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.3);
  border-radius: 4px;
}

.rules-panel::-webkit-scrollbar-thumb:hover {
  background: rgba(255, 255, 255, 0.5);
}

.rules-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 28px;
  padding-bottom: 20px;
  border-bottom: 2px solid rgba(255, 255, 255, 0.2);
}

.rules-icon {
  width: 40px;
  height: 40px;
  background: linear-gradient(135deg, #08B6E0, #05AF6B);
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  flex-shrink: 0;
}

.rules-title {
  color: white;
  font-size: 24px;
  font-weight: 700;
  margin: 0;
  text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.5);
}

.rules-content {
  color: white;
}

.rules-section {
  margin-bottom: 32px;
  padding-bottom: 24px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.15);
}

.rules-section:last-child {
  border-bottom: none;
  margin-bottom: 0;
  padding-bottom: 0;
}

.rules-section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.rules-section-title {
  color: white;
  font-size: 18px;
  font-weight: 700;
  margin: 0;
  text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.5);
  color: #4ade80;
}

.rules-badge {
  background: linear-gradient(135deg, #4ade80, #22c55e);
  color: white;
  font-size: 11px;
  font-weight: 700;
  padding: 4px 10px;
  border-radius: 12px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.rules-badge.optional {
  background: linear-gradient(135deg, #08B6E0, #0599b3);
}

.rules-detail {
  margin-bottom: 14px;
}

.rules-label {
  color: rgba(255, 255, 255, 0.9);
  font-size: 13px;
  font-weight: 600;
  margin-bottom: 6px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.rules-code {
  display: block;
  background: rgba(0, 0, 0, 0.4);
  padding: 10px 14px;
  border-radius: 8px;
  font-family: 'Courier New', 'Monaco', monospace;
  color: #4ade80;
  font-weight: 600;
  font-size: 13px;
  border: 1px solid rgba(74, 222, 128, 0.3);
  word-break: break-all;
}

.rules-code-inline {
  background: rgba(0, 0, 0, 0.4);
  padding: 3px 8px;
  border-radius: 4px;
  font-family: 'Courier New', 'Monaco', monospace;
  color: #4ade80;
  font-weight: 600;
  font-size: 13px;
  border: 1px solid rgba(74, 222, 128, 0.3);
}

.rules-example-box {
  margin: 18px 0;
  padding: 14px;
  background: rgba(74, 222, 128, 0.15);
  border-left: 4px solid #4ade80;
  border-radius: 8px;
}

.rules-example-label {
  color: rgba(255, 255, 255, 0.9);
  font-size: 12px;
  font-weight: 600;
  margin-bottom: 8px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.rules-example-code {
  display: block;
  font-family: 'Courier New', 'Monaco', monospace;
  color: #256e40;
  font-weight: 600;
  font-size: 14px;
  word-break: break-all;
}

.rules-list {
  margin: 20px 0 0 0;
  padding: 0;
  list-style: none;
}

.rules-list li {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  margin: 12px 0;
  line-height: 1.6;
  color: rgba(255, 255, 255, 0.9);
  font-size: 14px;
}

.list-icon {
  color: #4ade80;
  font-weight: 700;
  font-size: 16px;
  flex-shrink: 0;
  margin-top: 2px;
}

.rules-note {
  color: rgba(255, 255, 255, 0.8);
  font-size: 13px;
  line-height: 1.6;
  margin-top: 12px;
  font-style: italic;
}

/* Right Column: Upload Panel */
.upload-panel {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.upload-container {
  display: flex;
  justify-content: center;
  align-items: center;
  margin-top: 0;
}

.upload-area {
  background: rgba(255, 255, 255, 0.12);
  backdrop-filter: blur(20px);
  border: 2px dashed rgba(255, 255, 255, 0.3);
  border-radius: 20px;
  padding: 50px 30px;
  text-align: center;
  transition: all 0.3s ease;
  cursor: pointer;
  width: 100%;
  min-height: 320px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
  box-sizing: border-box;
}

.upload-area:hover {
  border-color: rgba(255, 255, 255, 0.6);
  background: rgba(255, 255, 255, 0.15);
}

.upload-icon {
  margin-bottom: 20px;
}

.upload-icon svg {
  filter: drop-shadow(0 2px 4px rgba(0, 0, 0, 0.3));
}

.upload-title {
  color: white;
  font-size: 24px;
  margin-bottom: 10px;
  font-weight: 600;
}

.upload-subtitle {
  color: rgba(255, 255, 255, 0.8);
  font-size: 16px;
  margin-bottom: 30px;
}

.file-input {
  display: none;
}

.browse-button {
  background: rgba(255, 255, 255, 0.2);
  color: white;
  border: 2px solid rgba(255, 255, 255, 0.3);
  padding: 12px 24px;
  border-radius: 8px;
  font-size: 16px;
  cursor: pointer;
  transition: all 0.3s ease;
  backdrop-filter: blur(10px);
}

.browse-button:hover:not(:disabled) {
  background: rgba(255, 255, 255, 0.3);
  border-color: rgba(255, 255, 255, 0.5);
  transform: translateY(-2px);
}

.browse-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Segmentation Selector Card */
.segmentation-selector-card {
  margin-top: 7%;
  background: rgba(255, 255, 255, 0.12);
  backdrop-filter: blur(20px);
  border-radius: 16px;
  padding: 24px;
  border: 1px solid rgba(255, 255, 255, 0.2);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
}

.selector-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 16px;
}

.selector-icon {
  width: 32px;
  height: 32px;
  background: linear-gradient(135deg, #3b82f6, #2563eb);
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  flex-shrink: 0;
}

.selector-label {
  color: white;
  font-weight: 700;
  font-size: 16px;
  margin: 0;
  text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.5);
}

/* Upload Area States */
.upload-area.dragging {
  border-color: rgba(74, 222, 128, 0.6);
  background: rgba(74, 222, 128, 0.1);
}

.upload-area.uploading {
  border-color: rgba(255, 255, 255, 0.5);
  background: rgba(255, 255, 255, 0.05);
}

/* Upload Progress */
.upload-progress {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 20px;
  padding: 40px;
}

.progress-spinner {
  width: 50px;
  height: 50px;
  border: 4px solid rgba(255, 255, 255, 0.3);
  border-top-color: #4ade80;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.progress-text {
  color: white;
  font-size: 18px;
  font-weight: 600;
  text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.5);
}

.progress-bar {
  width: 100%;
  max-width: 400px;
  height: 20px;
  background: rgba(255, 255, 255, 0.2);
  border-radius: 10px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(to right, #4ade80, #22c55e);
  transition: width 0.3s ease;
}

.progress-percentage {
  color: white;
  font-size: 16px;
  font-weight: 600;
  text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.5);
}

.progress-stage {
  color: rgba(255, 255, 255, 0.8);
  font-size: 14px;
  margin-top: 8px;
  font-style: italic;
  text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.5);
}

/* Selected Files */
.selected-files {
  background: rgba(255, 255, 255, 0.12);
  backdrop-filter: blur(20px);
  border-radius: 16px;
  padding: 24px;
  width: 100%;
  border: 1px solid rgba(255, 255, 255, 0.2);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
}

.selected-title {
  color: white;
  font-size: 20px;
  font-weight: 600;
  margin-bottom: 16px;
  text-align: center;
  text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.5);
}

.files-list {
  max-height: 300px;
  overflow-y: auto;
  margin-bottom: 20px;
}

.file-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px;
  margin-bottom: 8px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 8px;
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.file-item.invalid {
  border-color: rgba(239, 68, 68, 0.5);
  background: rgba(239, 68, 68, 0.1);
}

.file-name {
  color: white;
  font-size: 14px;
  flex: 1;
  text-align: left;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-status {
  font-size: 12px;
  font-weight: 600;
  padding: 4px 8px;
  border-radius: 4px;
}

.file-status.valid {
  color: #4ade80;
  background: rgba(74, 222, 128, 0.2);
}

.file-status.invalid {
  color: #ef4444;
  background: rgba(239, 68, 68, 0.2);
}

.method-select {
  width: 100%;
  padding: 12px 16px;
  background: rgba(255, 255, 255, 0.15);
  border: 2px solid rgba(255, 255, 255, 0.25);
  border-radius: 10px;
  color: white;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
  margin-bottom: 16px;
}

.method-select:hover {
  background: rgba(255, 255, 255, 0.2);
  border-color: rgba(255, 255, 255, 0.4);
  transform: translateY(-1px);
}

.method-select:focus {
  outline: none;
  border-color: #08B6E0;
  box-shadow: 0 0 0 4px rgba(8, 182, 224, 0.25);
  background: rgba(255, 255, 255, 0.2);
}

.method-select option {
  background: #1a1a1a;
  color: white;
  padding: 10px;
}

.method-info {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-top: 4px;
}

.method-info-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 12px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 8px;
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.method-info-badge {
  display: inline-block;
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  flex-shrink: 0;
  min-width: 70px;
  text-align: center;
}

.method-info-badge.sam3 {
  background: linear-gradient(135deg, #4ade80, #22c55e);
  color: white;
}

.method-info-badge.rmbg {
  background: linear-gradient(135deg, #08B6E0, #0599b3);
  color: white;
}

.method-info-text {
  color: rgba(255, 255, 255, 0.85);
  font-size: 13px;
  line-height: 1.5;
  flex: 1;
}

.upload-actions {
  display: flex;
  gap: 12px;
  justify-content: center;
}

.upload-btn {
  background: linear-gradient(135deg, #4ade80, #22c55e);
  color: white;
  border: none;
  padding: 12px 32px;
  border-radius: 8px;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
}

.upload-btn:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(74, 222, 128, 0.4);
}

.upload-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.clear-btn {
  background: rgba(255, 255, 255, 0.2);
  color: white;
  border: 2px solid rgba(255, 255, 255, 0.3);
  padding: 12px 24px;
  border-radius: 8px;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
}

.clear-btn:hover {
  background: rgba(255, 255, 255, 0.3);
  border-color: rgba(255, 255, 255, 0.5);
}

/* Error Message */
.error-message {
  margin-top: 20px;
  background: rgba(239, 68, 68, 0.2);
  border: 2px solid rgba(239, 68, 68, 0.5);
  border-radius: 12px;
  padding: 16px;
  color: white;
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
  backdrop-filter: blur(10px);
  box-sizing: border-box;
  gap: 12px;
}

.error-message p {
  word-break: break-word;
  flex: 1;
  min-width: 0;
}

.error-message p {
  margin: 0;
  flex: 1;
}

.close-error {
  background: none;
  border: none;
  color: white;
  font-size: 24px;
  cursor: pointer;
  padding: 0 8px;
  line-height: 1;
}

.close-error:hover {
  color: #ef4444;
}

/* Failure Page */
.failure-page {
  background: rgba(255, 255, 255, 0.12);
  backdrop-filter: blur(20px);
  border-radius: 20px;
  padding: 50px 30px;
  text-align: center;
  width: 100%;
  border: 2px solid rgba(239, 68, 68, 0.5);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
}

.failure-icon {
  margin-bottom: 24px;
  animation: scaleIn 0.5s ease;
}

.failure-title {
  color: white;
  font-size: 36px;
  font-weight: 700;
  margin-bottom: 16px;
  text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.5);
}

.failure-message {
  color: rgba(255, 255, 255, 0.9);
  font-size: 18px;
  margin-bottom: 30px;
  text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.5);
}

.failure-details {
  background: rgba(255, 255, 255, 0.05);
  border-radius: 12px;
  padding: 24px;
  margin-bottom: 30px;
  text-align: left;
}

.failure-details p {
  color: white;
  font-size: 16px;
  margin: 12px 0;
  line-height: 1.6;
}

.failure-details strong {
  color: #ef4444;
}

.error-text {
  color: #fca5a5 !important;
}

.error-note {
  color: #fca5a5 !important;
  font-style: italic;
  margin-top: 16px !important;
  padding-top: 16px;
  border-top: 1px solid rgba(239, 68, 68, 0.3);
}

.failure-actions {
  display: flex;
  gap: 16px;
  justify-content: center;
}

/* Success Page */
.success-page {
  background: rgba(255, 255, 255, 0.12);
  backdrop-filter: blur(20px);
  border-radius: 20px;
  padding: 50px 30px;
  text-align: center;
  width: 100%;
  border: 2px solid rgba(74, 222, 128, 0.3);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
}

.success-icon {
  margin-bottom: 24px;
  animation: scaleIn 0.5s ease;
}

@keyframes scaleIn {
  from {
    transform: scale(0);
    opacity: 0;
  }
  to {
    transform: scale(1);
    opacity: 1;
  }
}

.success-title {
  color: white;
  font-size: 36px;
  font-weight: 700;
  margin-bottom: 16px;
  text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.5);
}

.success-message {
  color: rgba(255, 255, 255, 0.9);
  font-size: 18px;
  margin-bottom: 30px;
  text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.5);
}

.success-details {
  background: rgba(255, 255, 255, 0.05);
  border-radius: 12px;
  padding: 24px;
  margin-bottom: 30px;
  text-align: left;
}

.success-details p {
  color: white;
  font-size: 16px;
  margin: 12px 0;
  line-height: 1.6;
}

.success-details strong {
  color: #4ade80;
}

.warning-text {
  color: #fbbf24 !important;
}

.success-actions {
  display: flex;
  gap: 16px;
  justify-content: center;
}

.upload-another-btn {
  background: linear-gradient(135deg, #4ade80, #22c55e);
  color: white;
  border: none;
  padding: 12px 24px;
  border-radius: 8px;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
}

.upload-another-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(74, 222, 128, 0.4);
}

.view-analysis-btn {
  background: linear-gradient(135deg, #3b82f6, #2563eb);
  color: white;
  border: none;
  padding: 12px 24px;
  border-radius: 8px;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
  box-shadow: 0 2px 8px rgba(59, 130, 246, 0.3);
}

.view-analysis-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.5);
  background: linear-gradient(135deg, #2563eb, #1d4ed8);
}

.back-btn {
  background: rgba(255, 255, 255, 0.2);
  color: white;
  border: 2px solid rgba(255, 255, 255, 0.3);
  padding: 12px 24px;
  border-radius: 8px;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
}

.back-btn:hover {
  background: rgba(255, 255, 255, 0.3);
  border-color: rgba(255, 255, 255, 0.5);
  transform: translateY(-2px);
}

/* Responsive design */

/* Large screens (1440px and above) */
@media (min-width: 1440px) {
  .content {
    max-width: 1400px;
  }
  
  .main-content-grid {
    max-width: 1400px;
    gap: 40px;
  }
}

/* Medium-large screens (1200px - 1024px) */
@media (max-width: 1200px) {
  .main-content-grid {
    grid-template-columns: 1fr 1fr;
    gap: 28px;
  }
  
  .content {
    max-width: 100%;
    padding: 0 20px;
  }
  
  .title {
    font-size: 65px;
  }
  
  .upload-area {
    width: 95%;
  }
}

/* Tablets (1024px and below) */
@media (max-width: 1024px) {
  .main-content-grid {
    grid-template-columns: 1fr;
    gap: 24px;
  }
  
  .rules-panel {
    position: static;
    max-height: none;
  }
  
  .app-content {
    padding-top: 180px;
    padding-left: 20px;
    padding-right: 20px;
  }
  
  .content {
    max-width: 100%;
  }
  
  .title {
    font-size: 56px;
  }
  
  .description {
    max-width: 500px;
  }
  
  .upload-area {
    width: 100%;
  }
  
  .segmentation-selector-card {
    margin-top: 0;
  }
}

/* Medium tablets and small laptops (900px - 768px) */
@media (max-width: 900px) {
  .title {
    font-size: 50px;
  }
  
  .description {
    font-size: 18px;
    max-width: 450px;
  }
  
  .rules-panel,
  .segmentation-selector-card {
    padding: 24px;
  }
  
  .upload-area {
    padding: 45px 25px;
    min-height: 300px;
  }
  
  .upload-title {
    font-size: 22px;
  }
  
  .upload-subtitle {
    font-size: 15px;
  }
  
  .back-button {
    top: 170px;
    left: 30px;
  }
}

/* Mobile devices (768px and below) */
@media (max-width: 768px) {
  .title {
    font-size: 42px;
  }
  
  .description {
    font-size: 16px;
    max-width: 100%;
    padding: 0 10px;
  }
  
  .main-content-grid {
    gap: 20px;
  }
  
  .rules-panel,
  .segmentation-selector-card {
    padding: 20px;
  }
  
  .upload-area {
    padding: 40px 20px;
    min-height: 280px;
    width: 100%;
  }
  
  .upload-title {
    font-size: 20px;
  }
  
  .upload-subtitle {
    font-size: 14px;
  }
  
  .upload-icon svg {
    width: 56px;
    height: 56px;
  }
  
  .rules-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
  }
  
  .rules-title {
    font-size: 20px;
  }
  
  .rules-section-title {
    font-size: 16px;
  }
  
  .method-info-item {
    flex-direction: column;
    gap: 8px;
  }
  
  .method-info-badge {
    align-self: flex-start;
  }
  
  .app-content {
    padding-top: 160px;
    padding-left: 15px;
    padding-right: 15px;
  }
  
  .back-button {
    top: 160px;
    left: 15px;
    padding: 6px;
  }
  
  .back-button svg {
    width: 28px;
    height: 28px;
  }
  
  .rules-panel {
    top: auto;
  }
  
  .title-container {
    gap: 15px;
    margin-bottom: 15px;
  }
  
  .selected-files {
    padding: 20px;
  }
  
  .error-message {
    padding: 14px;
    flex-wrap: wrap;
  }
  
  .error-message p {
    font-size: 14px;
  }
  
  .upload-progress {
    padding: 35px 20px;
  }
  
  .progress-bar {
    max-width: 100%;
  }
  
  .selected-title {
    font-size: 18px;
  }
  
  .file-item {
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
    padding: 10px;
  }
  
  .file-name {
    font-size: 13px;
    width: 100%;
  }
  
  .upload-actions {
    flex-direction: column;
    width: 100%;
  }
  
  .upload-btn,
  .clear-btn {
    width: 100%;
  }
  
  .success-page,
  .failure-page {
    padding: 40px 20px;
  }
  
  .success-title,
  .failure-title {
    font-size: 28px;
  }
  
  .success-message,
  .failure-message {
    font-size: 16px;
  }
  
  .success-actions,
  .failure-actions {
    flex-direction: column;
    gap: 12px;
  }
  
  .view-analysis-btn,
  .upload-another-btn,
  .back-btn {
    width: 100%;
  }
  
  .success-details,
  .failure-details {
    padding: 20px;
  }
  
  .success-details p,
  .failure-details p {
    font-size: 14px;
  }
}

/* Small mobile devices (480px and below) */
@media (max-width: 480px) {
  .title {
    font-size: 36px;
  }
  
  .description {
    font-size: 15px;
    margin-bottom: 30px;
  }
  
  .app-content {
    padding-top: 140px;
    padding-left: 10px;
    padding-right: 10px;
    padding-bottom: 40px;
  }
  
  .rules-panel,
  .segmentation-selector-card,
  .selected-files {
    padding: 16px;
    border-radius: 16px;
  }
  
  .upload-area {
    padding: 30px 15px;
    min-height: 250px;
    border-radius: 16px;
  }
  
  .upload-title {
    font-size: 18px;
  }
  
  .upload-subtitle {
    font-size: 13px;
    margin-bottom: 20px;
  }
  
  .upload-icon svg {
    width: 48px;
    height: 48px;
  }
  
  .browse-button {
    padding: 10px 20px;
    font-size: 14px;
  }
  
  .rules-title {
    font-size: 18px;
  }
  
  .rules-section-title {
    font-size: 15px;
  }
  
  .rules-code,
  .rules-example-code {
    font-size: 12px;
    padding: 8px 12px;
  }
  
  .rules-list li {
    font-size: 13px;
  }
  
  .method-select {
    padding: 10px 14px;
    font-size: 14px;
  }
  
  .method-info-text {
    font-size: 12px;
  }
  
  .back-button {
    top: 140px;
    left: 10px;
    padding: 5px;
  }
  
  .back-button svg {
    width: 24px;
    height: 24px;
  }
  
  .title-container {
    margin-bottom: 10px;
  }
  
  .success-page,
  .failure-page {
    padding: 30px 15px;
  }
  
  .success-icon svg,
  .failure-icon svg {
    width: 80px;
    height: 80px;
  }
  
  .success-title,
  .failure-title {
    font-size: 24px;
  }
  
  .success-message,
  .failure-message {
    font-size: 15px;
  }
  
  .success-details,
  .failure-details {
    padding: 16px;
  }
  
  .success-details p,
  .failure-details p {
    font-size: 13px;
    margin: 10px 0;
  }
  
  .progress-text {
    font-size: 16px;
  }
  
  .progress-percentage {
    font-size: 14px;
  }
  
  .progress-stage {
    font-size: 13px;
  }
  
  .error-message {
    padding: 12px;
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
  }
  
  .error-message p {
    font-size: 13px;
  }
  
  .close-error {
    align-self: flex-end;
    font-size: 20px;
  }
  
  .files-list {
    max-height: 200px;
  }
  
  .upload-progress {
    padding: 30px 20px;
  }
  
  .progress-bar {
    max-width: 100%;
  }
  
  .progress-spinner {
    width: 40px;
    height: 40px;
  }
}

/* Extra small devices (360px and below) */
@media (max-width: 360px) {
  .title {
    font-size: 32px;
  }
  
  .description {
    font-size: 14px;
  }
  
  .app-content {
    padding-top: 130px;
  }
  
  .upload-area {
    padding: 25px 12px;
    min-height: 220px;
  }
  
  .upload-title {
    font-size: 16px;
  }
  
  .upload-subtitle {
    font-size: 12px;
  }
  
  .rules-panel,
  .segmentation-selector-card {
    padding: 14px;
  }
  
  .back-button {
    top: 130px;
    left: 8px;
  }
}
</style>
