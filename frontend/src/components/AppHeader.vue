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
        <img src="../assets/agrilife_logo.png" alt="Texas A&M AgriLife Logo">
    </header>
  </main>
</template>

<script>
export default {
  props:{
    whiteBars: Array
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
  }
}
</script>

<style scoped>
/* Header */
.header {
  position: fixed;
  left: 0;
  right: 0;
  top: 50px;
  z-index: 4;
  transform: scale(1.60);
}

/* White bars styling */
.white-bars-container {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none; /* Allow clicks to pass through */
  z-index: 1; /* Above background but below interactive content */
}

.white-bar {
  position: absolute;
  background-color: white;
  opacity: 0.0;
  transition: all 0.3s ease;
}
</style>