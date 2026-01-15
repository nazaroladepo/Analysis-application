<template>
  <div class="dropdown-container" :class="containerClasses">
    <!-- Label -->
    <label v-if="label" class="dropdown-label" :for="dropdownId">
      {{ label }}
    </label>
    
    <!-- Dropdown Button -->
    <div 
      class="dropdown-button"
      :class="dropdownClasses"
      @click="toggleDropdown"
      @keydown.enter="toggleDropdown"
      @keydown.space.prevent="toggleDropdown"
      @keydown.escape="closeDropdown"
      @keydown.arrow-down.prevent="openDropdown"
      tabindex="0"
      :id="dropdownId"
    >
      <span class="dropdown-content">
        {{ displayText }}
      </span>
      
      <div class="dropdown-arrow" :class="{ 'arrow-up': isOpen }">
        <svg width="12" height="12" viewBox="0 0 12 12" fill="currentColor">
          <path d="M6 8L2 4h8l-4 4z"/>
        </svg>
      </div>
    </div>
    
    <!-- Dropdown Menu -->
    <transition name="dropdown-fade">
      <div 
        v-if="isOpen" 
        class="dropdown-menu"
      >
        <div 
          v-if="searchable" 
          class="dropdown-search"
        >
          <input
            ref="searchInput"
            v-model="searchQuery"
            type="text"
            class="search-input"
            :placeholder="searchPlaceholder"
            @keydown.escape="closeDropdown"
            @keydown.enter.prevent="selectFirstFiltered"
          />
        </div>
        
        <div class="dropdown-options" :style="{ maxHeight: maxHeight }">
          <div
            v-for="(option, index) in filteredOptions"
            :key="getOptionKey(option, index)"
            class="dropdown-option"
            :class="getOptionClasses(option)"
            @click="selectOption(option)"
            @mouseenter="hoveredIndex = index"
          >
            <span class="option-text">{{ getDisplayText(option) }}</span>
            <span v-if="isSelected(option)" class="selected-check">✓</span>
          </div>
          
          <div v-if="filteredOptions.length === 0" class="no-options">
            {{ noOptionsText }}
          </div>
        </div>
      </div>
    </transition>
    
    <!-- Error Message -->
    <div v-if="error" class="error-message">
      {{ error }}
    </div>
  </div>
</template>

<script>
export default {
  name: 'ConfigurableDropdown',
  props: {
    // Basic props
    modelValue: {
      type: [String, Number, Object, Array],
      default: null
    },
    
    options: {
      type: Array,
      required: true
    },
    
    // Display configuration
    label: {
      type: String,
      default: null
    },
    
    
    // Display text from parent component
    displayText: {
      type: String,
      default: null
    },
    
    // Option configuration
    optionLabel: {
      type: String,
      default: 'label'
    },
    
    optionValue: {
      type: String,
      default: 'value'
    },
    
    // Validation
    error: {
      type: String,
      default: null
    },
    
    // Functionality
    searchable: {
      type: Boolean,
      default: false
    },
    
    searchPlaceholder: {
      type: String,
      default: 'Search options...'
    },
    
    multiple: {
      type: Boolean,
      default: false
    },
    
    disabled: {
      type: Boolean,
      default: false
    },
    
    // Styling
    size: {
      type: String,
      default: 'medium',
      validator: (value) => ['small', 'medium', 'large'].includes(value)
    },
    
    maxHeight: {
      type: String,
      default: '200px'
    },
    
    fullWidth: {
      type: Boolean,
      default: false
    },
    
    // Text customization
    noOptionsText: {
      type: String,
      default: 'No options available'
    }
  },
  
  data() {
    return {
      isOpen: false,
      searchQuery: '',
      hoveredIndex: -1,
      dropdownId: `dropdown-${Math.random().toString(36).substr(2, 9)}`
    };
  },
  
  computed: {
    containerClasses() {
      return [
        'dropdown-wrapper',
        {
          'dropdown-disabled': this.disabled,
          'dropdown-error': this.error,
          'dropdown-full-width': this.fullWidth
        }
      ];
    },
    
    dropdownClasses() {
      return [
        'dropdown-trigger',
        `dropdown-${this.size}`,
        {
          'dropdown-open': this.isOpen,
          'dropdown-disabled': this.disabled,
          'dropdown-has-value': this.modelValue
        }
      ];
    },
    
    selectedOption() {
      if (this.multiple) {
        return this.modelValue || [];
      }
      
      if (!this.modelValue) {
        return null;
      }
      
      const found = this.options.find(option => 
        this.getOptionValue(option) === this.modelValue
      );
      
      return found || null;
    },
    
    filteredOptions() {
      if (!this.searchable || !this.searchQuery) {
        return this.options;
      }
      
      return this.options.filter(option => {
        const text = this.getDisplayText(option).toLowerCase();
        return text.includes(this.searchQuery.toLowerCase());
      });
    }
  },
  
  methods: {
    toggleDropdown() {
      if (this.disabled) return;
      
      if (this.isOpen) {
        this.closeDropdown();
      } else {
        this.openDropdown();
      }
    },
    
    openDropdown() {
      if (this.disabled) return;
      
      this.isOpen = true;
      this.searchQuery = '';
      
      if (this.searchable) {
        this.$nextTick(() => {
          this.$refs.searchInput?.focus();
        });
      }
    },
    
    closeDropdown() {
      this.isOpen = false;
      this.hoveredIndex = -1;
    },
    
    selectOption(option) {
      if (this.multiple) {
        const currentValue = this.modelValue || [];
        const optionValue = this.getOptionValue(option);
        
        if (this.isSelected(option)) {
          // Remove from selection
          const newValue = currentValue.filter(item => 
            this.getOptionValue(item) !== optionValue
          );
          this.$emit('update:modelValue', newValue);
        } else {
          // Add to selection
          this.$emit('update:modelValue', [...currentValue, option]);
        }
      } else {
        // Emit the option value, not the entire option object
        const optionValue = this.getOptionValue(option);
        this.$emit('update:modelValue', optionValue);
        this.closeDropdown();
      }
      
      this.$emit('change', option);
    },
    
    selectFirstFiltered() {
      if (this.filteredOptions.length > 0) {
        this.selectOption(this.filteredOptions[0]);
      }
    },
    
    isSelected(option) {
      if (this.multiple) {
        const currentValue = this.modelValue || [];
        return currentValue.some(item => 
          this.getOptionValue(item) === this.getOptionValue(option)
        );
      }
      
      // Compare directly with modelValue instead of selectedOption
      return this.getOptionValue(this.modelValue) === this.getOptionValue(option);
    },
    
    getDisplayText(option) {
      if (!option) return '';
      
      if (typeof option === 'string' || typeof option === 'number') {
        return option.toString();
      }
      
      return option[this.optionLabel] || option.toString();
    },
    
    getOptionValue(option) {
      if (!option) return '';
      
      if (typeof option === 'string' || typeof option === 'number') {
        return option;
      }
      
      return option[this.optionValue] || option;
    },
    
    getOptionKey(option, index) {
      return this.getOptionValue(option) || index;
    },
    
    getOptionClasses(option) {
      return {
        'option-selected': this.isSelected(option),
        'option-hovered': this.hoveredIndex === this.filteredOptions.indexOf(option)
      };
    },
    
    // Click outside handler
    handleClickOutside(event) {
      // Check if the click was outside the dropdown component
      if (this.$el && !this.$el.contains(event.target)) {
        this.closeDropdown();
      }
    }
  },
  
  mounted() {
    document.addEventListener('click', this.handleClickOutside);
  },
  
  beforeUnmount() {
    document.removeEventListener('click', this.handleClickOutside);
  },
  
  emits: ['update:modelValue', 'change']
}
</script>

<style scoped>
.dropdown-container {
  position: relative;
  display: inline-block;
}

.dropdown-wrapper {
  position: relative;
  display: inline-block;
}

.dropdown-full-width {
  width: 100%;
}

.dropdown-disabled {
  opacity: 0.5;
  cursor: not-allowed;
  pointer-events: none;
}

.dropdown-error {
  border-color: #ef4444 !important;
}

.dropdown-label {
  display: block;
  margin-bottom: 6px;
  font-weight: 500;
  color: white;
  font-size: 14px;
}

.dropdown-button {
  display: flex;
  align-items: center;
  justify-content: space-between;
  cursor: pointer;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-radius: 30px;
  background: rgba(255, 255, 255, 0.575);
  color: white;
  backdrop-filter: blur(10px);
  transition: all 0.3s ease;
  outline: none;
  position: relative;
}

.dropdown-trigger {
  display: flex;
  align-items: center;
  justify-content: space-between;
  cursor: pointer;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-radius: 30px;
  background: rgba(255, 255, 255, 0.575);
  color: white;
  backdrop-filter: blur(10px);
  transition: all 0.3s ease;
  outline: none;
  position: relative;
}

/* Dropdown Sizes */
.dropdown-small {
  padding: 8px 12px;
  font-size: 14px;
  min-height: 36px;
}

.dropdown-medium {
  padding: 12px 16px;
  font-size: 16px;
  min-height: 44px;
}

.dropdown-large {
  padding: 16px 20px;
  font-size: 18px;
  min-height: 52px;
}

.dropdown-trigger.dropdown-small {
  padding: 8px 12px;
  font-size: 14px;
  min-height: 36px;
}

.dropdown-trigger.dropdown-medium {
  padding: 12px 16px;
  font-size: 16px;
  min-height: 44px;
}

.dropdown-trigger.dropdown-large {
  padding: 16px 20px;
  font-size: 18px;
  min-height: 52px;
}

/* Dropdown States */
.dropdown-button:hover:not(.dropdown-disabled) {
  border-color: rgba(255, 255, 255, 0.6);
  transform: translateY(-1px);
}

.dropdown-trigger:hover:not(.dropdown-disabled) {
  border-color: rgba(255, 255, 255, 0.6);
  transform: translateY(-1px);
}

.dropdown-button:focus {
  border-color: #ffffff;
  box-shadow: 0 0 0 3px rgba(79, 172, 254, 0.3);
}

.dropdown-trigger:focus {
  border-color: #ffffff;
  box-shadow: 0 0 0 3px rgba(79, 172, 254, 0.3);
}

.dropdown-open {
  border-color: #ffffff !important;
}

.dropdown-trigger.dropdown-open {
  border-color: #ffffff !important;
}

.dropdown-trigger.dropdown-disabled {
  opacity: 0.5;
  cursor: not-allowed;
  pointer-events: none;
}

.dropdown-trigger.dropdown-has-value {
  border-color: rgba(255, 255, 255, 0.6);
}

/* Dropdown Content */
.dropdown-content {
  color: rgba(0, 0, 0, 0.8);
  flex: 1;
  text-align: center;
  font-size: 18px;
  font-weight: 800;
}

.selected-text {
  color: inherit;
}

.placeholder-text {
  color: rgba(0, 0, 0, 0.541);
}

.dropdown-arrow {
  margin-left: 8px;
  transition: transform 0.3s ease;
  color: rgba(255, 255, 255, 0.7);
}

.arrow-up {
  transform: rotate(180deg);
}

/* Dropdown Menu */
.dropdown-menu {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  z-index: 1000;
  margin-top: 4px;
  border-radius: 8px;
  border: 1px solid rgba(255, 255, 255, 0.2);
  background: rgb(255, 255, 255);
  backdrop-filter: blur(20px);
  box-shadow: 0 10px 25px rgba(0, 0, 0, 0.3);
  overflow: hidden;
}

.dropdown-search {
  padding: 8px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.search-input {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid rgba(255, 255, 255, 0.3);
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.1);
  color: rgb(0, 0, 0);
  font-size: 14px;
  outline: none;
}

.search-input::placeholder {
  color: rgba(0, 0, 0, 0.5);
}

.dropdown-options {
  overflow-y: auto;
}

.dropdown-option {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  cursor: pointer;
  transition: background-color 0.2s ease;
  color: rgb(0, 0, 0);
}

.dropdown-option:hover,
.option-hovered {
  background: rgba(255, 255, 255, 0.1);
}

.option-selected {
  background: rgba(79, 172, 254, 0.2);
  color: #4facfe;
}

.option-text {
  flex: 1;
}

.selected-check {
  color: #4facfe;
  font-weight: bold;
}

.no-options {
  padding: 16px;
  text-align: center;
  color: rgba(255, 255, 255, 0.6);
  font-style: italic;
}

.error-message {
  margin-top: 4px;
  font-size: 12px;
  color: #ef4444;
}

/* Transitions */
.dropdown-fade-enter-active,
.dropdown-fade-leave-active {
  transition: all 0.3s ease;
}

.dropdown-fade-enter-from {
  opacity: 0;
  transform: translateY(-10px);
}

.dropdown-fade-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}
</style>
