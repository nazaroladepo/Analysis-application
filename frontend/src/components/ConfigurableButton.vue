<template>
  <button 
    :class="buttonClasses"
    :style="buttonStyles"
    :disabled="disabled"
    @click="handleClick"
    @mouseenter="isHovered = true"
    @mouseleave="isHovered = false"
  >
    <span v-if="icon && iconPosition === 'left'" class="icon icon-left">
      <component :is="icon" />
    </span>
    
    <span class="button-text">{{ text }}</span>
    
    <span v-if="icon && iconPosition === 'right'" class="icon icon-right">
      <component :is="icon" />
    </span>
    
    <span v-if="loading" class="loading-spinner"></span>
  </button>
</template>

<script>
export default {
  name: 'ConfigurableButton',
  props: {
    // Button text
    text: {
      type: String,
      required: true
    },
    
    // Button variants
    variant: {
      type: String,
      default: 'primary',
      validator: (value) => ['primary', 'secondary', 'success', 'danger', 'warning', 'info', 'light', 'dark', 'outline'].includes(value)
    },
    
    // Button sizes
    size: {
      type: String,
      default: 'medium',
      validator: (value) => ['small', 'medium', 'large', 'extra-large'].includes(value)
    },
    
    // Button states
    disabled: {
      type: Boolean,
      default: false
    },
    
    loading: {
      type: Boolean,
      default: false
    },
    
    // Icon configuration
    icon: {
      type: [String, Object],
      default: null
    },
    
    iconPosition: {
      type: String,
      default: 'left',
      validator: (value) => ['left', 'right'].includes(value)
    },
    
    // Custom styling
    customColor: {
      type: String,
      default: null
    },
    
    customBackground: {
      type: String,
      default: null
    },
    
    borderRadius: {
      type: [String, Number],
      default: '8px'
    },
    
    fullWidth: {
      type: Boolean,
      default: false
    },
    
    // Animation options
    hoverEffect: {
      type: String,
      default: 'scale',
      validator: (value) => ['scale', 'lift', 'glow', 'none'].includes(value)
    }
  },
  
  data() {
    return {
      isHovered: false
    };
  },
  
  computed: {
    buttonClasses() {
      return [
        'configurable-button',
        `button-${this.variant}`,
        `button-${this.size}`,
        `hover-${this.hoverEffect}`,
        {
          'button-disabled': this.disabled,
          'button-loading': this.loading,
          'button-full-width': this.fullWidth,
          'button-with-icon': this.icon
        }
      ];
    },
    
    buttonStyles() {
      const styles = {
        borderRadius: typeof this.borderRadius === 'number' ? `${this.borderRadius}px` : this.borderRadius
      };
      
      if (this.customColor) {
        styles.color = this.customColor;
      }
      
      if (this.customBackground) {
        styles.backgroundColor = this.customBackground;
        styles.borderColor = this.customBackground;
      }
      
      return styles;
    }
  },
  
  methods: {
    handleClick(event) {
      if (!this.disabled && !this.loading) {
        this.$emit('click', event);
      }
    }
  },
  
  emits: ['click']
}
</script>

<style scoped>
.configurable-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  border: 2px solid transparent;
  cursor: pointer;
  font-weight: 500;
  text-decoration: none;
  transition: all 0.3s ease;
  position: relative;
  overflow: hidden;
  font-family: inherit;
  outline: none;
}

/* Button Variants */
.button-primary {
  background: #06ca78de;
  border-color: rgb(255, 255, 255);
  color: white;
}

.button-secondary {
  background: rgba(255, 255, 255, 0.1);
  color: white;
  border-color: rgba(255, 255, 255, 0.3);
  backdrop-filter: blur(10px);
}

.button-success {
  background: linear-gradient(135deg, #4ade80 0%, #22c55e 100%);
  color: white;
  border-color: rgba(34, 197, 94, 0.3);
}

.button-danger {
  background: linear-gradient(135deg, #f87171 0%, #ef4444 100%);
  color: white;
  border-color: rgba(239, 68, 68, 0.3);
}

.button-warning {
  background: linear-gradient(135deg, #fbbf24 0%, #f59e0b 100%);
  color: white;
  border-color: rgba(245, 158, 11, 0.3);
}

.button-info {
  background: linear-gradient(135deg, #60a5fa 0%, #3b82f6 100%);
  color: white;
  border-color: rgba(59, 130, 246, 0.3);
}

.button-light {
  background: rgba(255, 255, 255, 0.9);
  color: #333;
  border-color: rgba(255, 255, 255, 0.5);
}

.button-dark {
  background: rgba(0, 0, 0, 0.8);
  color: white;
  border-color: rgba(0, 0, 0, 0.5);
}

.button-outline {
  background: transparent;
  color: white;
  border-color: rgba(255, 255, 255, 0.5);
}

/* Button Sizes */
.button-small {
  padding: 6px 12px;
  font-size: 14px;
  min-height: 32px;
}

.button-medium {
  padding: 10px 20px;
  font-size: 16px;
  min-height: 40px;
}

.button-large {
  padding: 14px 28px;
  font-size: 18px;
  min-height: 48px;
}

.button-extra-large {
  padding: 18px 36px;
  font-size: 20px;
  min-height: 56px;
}

/* Button States */
.button-disabled {
  opacity: 0.5;
  cursor: not-allowed;
  pointer-events: none;
}

.button-loading {
  cursor: wait;
}

.button-loading .button-text {
  opacity: 0.7;
}

.button-full-width {
  width: 100%;
}

/* Icon Styling */
.icon {
  display: flex;
  align-items: center;
  justify-content: center;
}

.icon-left {
  margin-right: 4px;
}

.icon-right {
  margin-left: 4px;
}

/* Loading Spinner */
.loading-spinner {
  width: 16px;
  height: 16px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top: 2px solid currentColor;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  position: absolute;
  right: 12px;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

/* Hover Effects */
.hover-scale:hover:not(.button-disabled) {
  transform: scale(1.05);
}

.hover-lift:hover:not(.button-disabled) {
  transform: translateY(-2px);
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
}

.hover-glow:hover:not(.button-disabled) {
  box-shadow: 0 0 20px rgba(79, 172, 254, 0.5);
}

/* Outline variant hover */
.button-outline:hover:not(.button-disabled) {
  background: rgba(255, 255, 255, 0.1);
}

/* Focus styles */
.configurable-button:focus {
  box-shadow: 0 0 0 3px rgba(79, 172, 254, 0.3);
}

/* Active state */
.configurable-button:active:not(.button-disabled) {
  transform: scale(0.98);
}

/* Responsive design */
@media (max-width: 768px) {
  .button-small {
    padding: 5px 10px;
    font-size: 13px;
    min-height: 30px;
  }
  
  .button-medium {
    padding: 8px 16px;
    font-size: 15px;
    min-height: 38px;
  }
  
  .button-large {
    padding: 12px 24px;
    font-size: 16px;
    min-height: 44px;
  }
  
  .button-extra-large {
    padding: 14px 28px;
    font-size: 18px;
    min-height: 50px;
  }
  
  .configurable-button {
    gap: 6px;
  }
}

@media (max-width: 480px) {
  .button-small {
    padding: 4px 8px;
    font-size: 12px;
    min-height: 28px;
  }
  
  .button-medium {
    padding: 8px 14px;
    font-size: 14px;
    min-height: 36px;
  }
  
  .button-large {
    padding: 10px 20px;
    font-size: 15px;
    min-height: 40px;
  }
  
  .button-extra-large {
    padding: 12px 24px;
    font-size: 16px;
    min-height: 46px;
  }
  
  .loading-spinner {
    width: 14px;
    height: 14px;
  }
}
</style>
