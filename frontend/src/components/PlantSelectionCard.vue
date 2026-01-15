<template>
  <div class="card">
    <h1 class="card-title">{{ title }}</h1>
    <div class="title-underline"></div>
    <div class="plant-list">
      <button
        v-for="plant in plants"
        :key="plant.name || plant"
        :class="{
          'selected': selectedPlant === (plant.name || plant),
          'disabled': plant.disabled
        }"
        :disabled="plant.disabled"
        @click="handlePlantClick(plant)"
      >
        {{ plant.name || plant }}
      </button>
    </div>
  </div>
</template>

<script>
export default {
  props: {
    title: String,
    plants: Array, // Can be array of strings or array of objects with {name, disabled}
    selectedPlant: String
  },
  emits: ['select-plant'],
  methods: {
    handlePlantClick(plant) {
      // Don't emit if plant is disabled
      if (plant.disabled) return;

      // Emit the plant name (handle both string and object formats)
      const speciesName = plant.name || plant;
      this.$emit('select-plant', speciesName);
    }
  }
}
</script>

<style scoped>
.card {
  border-radius: 50px;
  padding: 15px;
  margin: 10px;
  width: 300px;
  box-shadow: inset 0 4px 10px rgba(0, 0, 0, 0.233), inset 0 -4px 8px rgba(0, 0, 0, 0.2);
  background: #74b596b9;
  display: flex;
  flex-direction: column;
  
}

.card-title {
  font-size: 48px;
  margin-top: 5px;
  margin-bottom: 15px;
  color: white;
  font-weight: 600;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.3);
}

.title-underline {
  width: 70%;
  height: 4px;
  background-color: white;
  border-radius: 2px;
  margin: -15px auto 20px auto;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.3);
  opacity: 0.9;
}

.plant-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  width: 100%;
  align-items: center;
}

button {
  padding: 2px 0px;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-size: 48px;
  transition: all 0.3s ease;
  text-align: center;
  background-color: rgba(255, 255, 255, 0);
  width: 80%;
  font-weight: 500;
  color: #ffffff;
  position: relative;
  border-bottom: 3px solid transparent;
}

button:hover:not(.disabled) {
  background-color: rgba(255, 255, 255, 0);
  transform: translateY(-4px);
  border-bottom: 4px solid white;
  border-radius: 8px 8px 0 0;
  transition: border-bottom 0.2s ease;
}

button.disabled {
  background-color: rgba(255, 255, 255, 0);
  color: rgb(255, 255, 255);
  cursor: not-allowed;
  opacity: 0.5;
}

button:disabled {
  cursor: not-allowed;
}
</style>