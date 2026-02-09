<template>
   <!-- White bars container -->
   <main class="app-header-wrapper">
      <div class="white-bars-container">
        <div
          v-for="(bar, index) in whiteBars"
          :key="index"
          class="white-bar"
          :style="getBarStyle(bar)"
        ></div>
      </div>

   <header class="header">
        <img
          :src="logoImage"
          alt="Texas A&M AgriLife Logo"
          @error="handleLogoError"
        >
    </header>
  </main>
</template>

<script>
import bundledLogo from '@/assets/agrilife_logo.png'

export default {
  props:{
    whiteBars: Array
  },
  data() {
    return {
      logoImage: bundledLogo,
      hasTriedFallback: false
    }
  },
  methods: {
    // White bars methods
    getBarStyle(bar) {
      return {
        width: `${bar.width}px`,
        height: `${bar.height}px`,
        left: `${bar.x}px`,
        top: `${bar.y}px`,
        opacity: bar.opacity || 1.0,
        borderRadius: `${bar.height / 2}px` // Makes ends rounded
      };
    },
    handleLogoError() {
      if (!this.hasTriedFallback) {
        // Use a route-independent path as a fallback for edge-case bundling/cache issues.
        this.logoImage = `${process.env.BASE_URL || '/'}agrilife_logo.png`;
        this.hasTriedFallback = true;
      }
    }
  }
}
</script>

<style scoped>
.app-header-wrapper {
  position: fixed;
  inset: 0;
  z-index: 50;
  pointer-events: none;
}

/* Header */
.header {
  position: absolute;
  left: 0;
  right: 0;
  top: 50px;
  z-index: 2;
  transform: scale(1.60);
  display: flex;
  justify-content: center;
  align-items: center;
}

.header img {
  max-width: 100%;
  height: auto;
  display: block;
}

/* White bars styling */
.white-bars-container {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  z-index: 1;
}

.white-bar {
  position: absolute;
  background-color: white;
  opacity: 0.0;
  transition: all 0.3s ease;
}

/* Responsive design */
@media (max-width: 1024px) {
  .header {
    transform: scale(1.40);
    top: 40px;
  }
}

@media (max-width: 768px) {
  .header {
    transform: scale(1.20);
    top: 30px;
  }
  
  .header img {
    max-width: 90%;
  }
}

@media (max-width: 480px) {
  .header {
    transform: scale(1.00);
    top: 20px;
  }
  
  .header img {
    max-width: 80%;
  }
}

@media (max-width: 360px) {
  .header {
    transform: scale(0.90);
    top: 15px;
  }
  
  .header img {
    max-width: 75%;
  }
}
</style>