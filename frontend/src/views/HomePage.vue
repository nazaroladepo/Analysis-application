<template>
  <div id="home">
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
          <h1 class="title">Greenhouse Automatic <br> Phenotyping Tool</h1>
          <div class="documentation-icon" @click="openDocumentation">
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M14 2H6C4.9 2 4 2.9 4 4V20C4 21.1 4.89 22 5.99 22H18C19.1 22 20 21.1 20 20V8L14 2Z" stroke="white" stroke-width="2" fill="rgba(255,255,255,0.1)"/>
              <path d="M14 2V8H20" stroke="white" stroke-width="2" fill="none"/>
              <path d="M16 13H8" stroke="white" stroke-width="2"/>
              <path d="M16 17H8" stroke="white" stroke-width="2"/>
              <path d="M10 9H8" stroke="white" stroke-width="2"/>
            </svg>
            <div class="tooltip">Documentation</div>
          </div>
        </div>
        <div class="description">
          Analyze your plant images for biotic and abiotic greenhouses with advanced AI-powered tools.
        </div>
        
        <!-- Action Buttons -->
        <div class="action-buttons" v-if="currentView === null">
          <button 
            class="action-button" 
            :class="{ active: currentView === 'select' }"
            @click="setView('select')"
          >
            Select Plant
          </button>
          <button 
            class="action-button" 
            :class="{ active: currentView === 'upload' }"
            @click="setView('upload')"
          >
            Upload Data
          </button>
        </div>

        <!-- Plant Selection View -->
        <div v-if="currentView === 'select'" class="plant-selection-view"  >
          <div class="subtitle-container">
            <div class="back-arrow" @click="setView(null)" title="Back">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M19 12H5" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                <path d="M12 19L5 12L12 5" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
            </div>
            <h2 class="subtitle">Select Plant</h2>
          </div>
          <div class="title-underline"></div>

          <div class="selection-container">
            <PlantSelectionCard
              title="Biotic"
              :plants="[{name:'Sorghum', disabled: false}, {name: 'Uploaded', disabled: false},{name: 'Mullet', disabled: false}]"
              @select-plant="handlePlantSelection"
              :selectedPlant="selectedPlant"
            />
            <PlantSelectionCard
              title="Abiotic"
              :plants="[{name:'Cotton', disabled: false}, {name: 'Corn', disabled: false}]"
              @select-plant="handlePlantSelection"
              :selectedPlant="selectedPlant"
            />
          </div>
        </div>
      </main>
    </div>
  </div>
</template>

<script>
import PlantSelectionCard from '../components/PlantSelectionCard.vue'
import AppHeader from '../components/AppHeader.vue'
import backgroundImage from '@/assets/greenhouse-img1.jpg'

export default {
  name: 'HomePage',
  components: {
    PlantSelectionCard,
    AppHeader
  },
  data() {
    return {
      selectedPlant: null,
      currentView: null, // 'select' or 'upload'
      
      // Background configuration
      backgroundImage: backgroundImage,
      backgroundImageOpacity: 0.8,
      
      // Gradient configuration
      gradientTopColor: '#08B6E0',
      gradientBottomColor: '#05AF6B',
      gradientOpacity: 0.7,
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
    }
  },
  methods: {
    setView(view) {
      if (view === 'upload') {
        // Navigate to upload data page
        this.$router.push({ name: 'UploadData' });
      } else if (view === 'select') {
        // Show plant selection view
        this.currentView = 'select';
      } else {
        // Show main menu
        this.currentView = null;
      }
    },
    
    handlePlantSelection(species) {
      // Navigate to plant details page using router
      this.$router.push({
        name: 'PlantDetails',
        params: { speciesName: species }
      });
    },
    
    openDocumentation() {
      window.open('https://plant-analysis-tool.readthedocs.io/en/latest/index.html', '_blank');
    },
    
    // Helper method to convert hex color to rgba with opacity
    hexToRgba(hex, opacity) {
      const r = parseInt(hex.slice(1, 3), 16);
      const g = parseInt(hex.slice(3, 5), 16);
      const b = parseInt(hex.slice(5, 7), 16);
      return `rgba(${r}, ${g}, ${b}, ${opacity})`;
    },
    
    // Background configuration methods
    setBackgroundImage(imageUrl) {
      this.backgroundImage = imageUrl;
    },
    
    setBackgroundImageOpacity(opacity) {
      this.backgroundImageOpacity = Math.max(0, Math.min(1, opacity));
    },
    
    setGradientColors(topColor, bottomColor) {
      this.gradientTopColor = topColor;
      this.gradientBottomColor = bottomColor;
    },
    
    setGradientOpacity(opacity) {
      this.gradientOpacity = Math.max(0, Math.min(1, opacity));
    }
  }
}
</script>

<style>
/* Global styles to remove scrollbars */
html, body {
  overflow: hidden;
  margin: 0;
  padding: 0;
  height: 100%;
  width: 100%;
}

/* Hide scrollbars for webkit browsers */
::-webkit-scrollbar {
  display: none;
}

/* Hide scrollbars for Firefox */
html {
  scrollbar-width: none;
}
</style>

<style scoped>
#home {
  font-family: Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  position: relative;
  height: 100vh;
  width: 100vw;
  overflow: hidden;
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

/* Gradient overlay */
.gradient-overlay {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
}

/* Content container */
.app-content {
  position: relative;
  z-index: 1;
  min-height: 97vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 20px;
  text-align: center;
}

.content {
  width: 100%;
  max-width: 1200px;
}

.title-container {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 20px;
  margin-top: 200px;
  margin-bottom: 20px;
}

.title {
  color: white;
  font-size: 73px;
  margin-top: -10px;
  margin-bottom: 0px;
  text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.5);
  font-weight: 900;
}

.documentation-icon {
  position: relative;
  top: 40px;
  left: 20px;
  cursor: pointer;
  padding: 8px;
  border-radius: 50%;
  transition: all 0.3s ease;
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(10px);
}

.documentation-icon:hover {
  background: rgba(255, 255, 255, 0.2);
  transform: scale(1.1);
}

.documentation-icon svg {
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

.documentation-icon:hover .tooltip {
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
  opacity: 1.0;
}

/* Action Buttons */
.action-buttons {
  display: flex;
  justify-content: center;
  gap: 80px;
  margin-bottom: 40px;
}

.action-button {
  background: #74b596b9;
  color: white;
  border: 2px solid rgba(255, 255, 255, 0);
  padding: 15px 30px;
  border-radius: 10px;
  font-size: 24px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
  backdrop-filter: blur(10px);
  width: 250px;
  height: 150px;
}

.action-button:hover {
  background: rgba(255, 255, 255, 0.2);
  border-color: rgba(255, 255, 255, 0.5);
  transform: translateY(-2px);
}

.action-button.active {
  background: rgba(255, 255, 255, 0.3);
  border-color: rgba(255, 255, 255, 0.7);
  box-shadow: 0 4px 15px rgba(255, 255, 255, 0.2);
}

/* Plant Selection View */
.plant-selection-view {
  margin-top: -40px;
  width: 100%;
}

.subtitle-container {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 15px;
  margin-bottom: 40px;
  margin-top: -80px;
}

.back-arrow {
  cursor: pointer;
  padding: 8px;
  border-radius: 50%;
  transition: all 0.3s ease;
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(10px);
  display: flex;
  position: fixed;
  left: 500px;
  bottom: 425px;
}

.back-arrow:hover {
  background: rgba(255, 255, 255, 0.2);
  transform: scale(1.2);
}

.back-arrow svg {
  filter: drop-shadow(0 2px 4px rgba(0, 0, 0, 0.3));
}

.subtitle {
  color: white;
  font-size: 60px;
  margin-bottom: 0;
  text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.5);
  font-weight: 500;
}

.title-underline {
  width: 30%;
  height: 6px;
  background-color: white;
  border-radius: 2px;
  margin: -35px auto 20px auto;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
  opacity: 0.9;
}

.selection-container {
  display: flex;
  height: 369px;
  flex-wrap: wrap;
  gap: 100px;
  justify-content: center;
}

/* Responsive design */
@media (max-width: 768px) {
  .title {
    font-size: 48px;
  }
  
  .subtitle {
    font-size: 36px;
  }
  
  .description {
    font-size: 16px;
    max-width: 350px;
  }
  
  .action-buttons {
    flex-direction: column;
    align-items: center;
    gap: 15px;
  }
  
  .action-button {
    min-width: 200px;
  }
  
  .selection-container {
    flex-direction: column;
    align-items: center;
    gap: 40px;
  }
}
</style>
