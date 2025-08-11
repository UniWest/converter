/**
 * Modern SVG Icon Library for Video to GIF Converter
 * Replaces emoji with clean, accessible SVG icons
 */

class IconLibrary {
    static icons = {
        // File types
        video: `<svg viewBox="0 0 24 24" fill="currentColor">
            <path d="M18 4l2 4h-3l-2-4h-2l2 4h-3l-2-4H8l2 4H7L5 4H4c-1.1 0-1.99.9-1.99 2L2 18c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V4h-4z"/>
            <polygon points="10,8 16,12 10,16"/>
        </svg>`,
        
        image: `<svg viewBox="0 0 24 24" fill="currentColor">
            <path d="M21 19V5c0-1.1-.9-2-2-2H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2zM8.5 13.5l2.5 3.01L14.5 12l4.5 6H5l3.5-4.5z"/>
        </svg>`,
        
        audio: `<svg viewBox="0 0 24 24" fill="currentColor">
            <path d="M12 3v10.55c-.59-.34-1.27-.55-2-.55-2.21 0-4 1.79-4 4s1.79 4 4 4 4-1.79 4-4V7h4V3h-6z"/>
        </svg>`,
        
        document: `<svg viewBox="0 0 24 24" fill="currentColor">
            <path d="M14,2H6A2,2 0 0,0 4,4V20A2,2 0 0,0 6,22H18A2,2 0 0,0 20,20V8L14,2M18,20H6V4H13V9H18V20Z"/>
        </svg>`,
        
        archive: `<svg viewBox="0 0 24 24" fill="currentColor">
            <path d="M14,17H12V15H14M14,13H12V11H14M14,9H12V7H14M10,17H8V15H10M10,13H8V11H10M10,9H8V7H10M10,5H8V3H10M14,5H12V3H14M7,2V4H4V6H20V4H17V2H7M20,8H4V19A2,2 0 0,0 6,21H18A2,2 0 0,0 20,19V8Z"/>
        </svg>`,
        
        batch: `<svg viewBox="0 0 24 24" fill="currentColor">
            <path d="M10,4H4C2.89,4 2,4.89 2,6V18A2,2 0 0,0 4,20H20A2,2 0 0,0 22,18V8C22,6.89 21.1,6 20,6H12L10,4Z"/>
            <path d="M8 12h8M8 16h5" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
        </svg>`,
        
        // Actions
        upload: `<svg viewBox="0 0 24 24" fill="currentColor">
            <path d="M14,2H6A2,2 0 0,0 4,4V20A2,2 0 0,0 6,22H18A2,2 0 0,0 20,20V8L14,2M18,20H6V4H13V9H18V20Z"/>
            <path d="M11 15l-4-4h3V7h2v4h3l-4 4z"/>
        </svg>`,
        
        download: `<svg viewBox="0 0 24 24" fill="currentColor">
            <path d="M5,20H19V18H5M19,9H15V3H9V9H5L12,16L19,9Z"/>
        </svg>`,
        
        convert: `<svg viewBox="0 0 24 24" fill="currentColor">
            <path d="M12,18A6,6 0 0,1 6,12A6,6 0 0,1 12,6A6,6 0 0,1 18,12A6,6 0 0,1 12,18M12,4A8,8 0 0,0 4,12A8,8 0 0,0 12,20A8,8 0 0,0 20,12A8,8 0 0,0 12,4M12,8A4,4 0 0,0 8,12A4,4 0 0,0 12,16A4,4 0 0,0 16,12A4,4 0 0,0 12,8Z"/>
            <path d="M15 9l-3 3-3-3h2V6h2v3h2z"/>
        </svg>`,
        
        play: `<svg viewBox="0 0 24 24" fill="currentColor">
            <path d="M8,5.14V19.14L19,12.14L8,5.14Z"/>
        </svg>`,
        
        pause: `<svg viewBox="0 0 24 24" fill="currentColor">
            <path d="M14,19H18V5H14M6,19H10V5H6V19Z"/>
        </svg>`,
        
        settings: `<svg viewBox="0 0 24 24" fill="currentColor">
            <path d="M12,15.5A3.5,3.5 0 0,1 8.5,12A3.5,3.5 0 0,1 12,8.5A3.5,3.5 0 0,1 15.5,12A3.5,3.5 0 0,1 12,15.5M19.43,12.97C19.47,12.65 19.5,12.33 19.5,12C19.5,11.67 19.47,11.34 19.43,11L21.54,9.37C21.73,9.22 21.78,8.95 21.66,8.73L19.66,5.27C19.54,5.05 19.27,4.96 19.05,5.05L16.56,6.05C16.04,5.66 15.5,5.32 14.87,5.07L14.5,2.42C14.46,2.18 14.25,2 14,2H10C9.75,2 9.54,2.18 9.5,2.42L9.13,5.07C8.5,5.32 7.96,5.66 7.44,6.05L4.95,5.05C4.73,4.96 4.46,5.05 4.34,5.27L2.34,8.73C2.22,8.95 2.27,9.22 2.46,9.37L4.57,11C4.53,11.34 4.5,11.67 4.5,12C4.5,12.33 4.53,12.65 4.57,12.97L2.46,14.63C2.27,14.78 2.22,15.05 2.34,15.27L4.34,18.73C4.46,18.95 4.73,19.03 4.95,18.95L7.44,17.94C7.96,18.34 8.5,18.68 9.13,18.93L9.5,21.58C9.54,21.82 9.75,22 10,22H14C14.25,22 14.46,21.82 14.5,21.58L14.87,18.93C15.5,18.68 16.04,18.34 16.56,17.94L19.05,18.95C19.27,19.03 19.54,18.95 19.66,18.73L21.66,15.27C21.78,15.05 21.73,14.78 21.54,14.63L19.43,12.97Z"/>
        </svg>`,
        
        // Status
        success: `<svg viewBox="0 0 24 24" fill="currentColor">
            <path d="M12,2A10,10 0 0,1 22,12A10,10 0 0,1 12,22A10,10 0 0,1 2,12A10,10 0 0,1 12,2M11,16.5L18,9.5L16.59,8.09L11,13.67L7.91,10.59L6.5,12L11,16.5Z"/>
        </svg>`,
        
        error: `<svg viewBox="0 0 24 24" fill="currentColor">
            <path d="M13,13H11V7H13M13,17H11V15H13M12,2A10,10 0 0,0 2,12A10,10 0 0,0 12,22A10,10 0 0,0 22,12A10,10 0 0,0 12,2Z"/>
        </svg>`,
        
        warning: `<svg viewBox="0 0 24 24" fill="currentColor">
            <path d="M13,13H11V7H13M12,17.3A1.3,1.3 0 0,1 10.7,16A1.3,1.3 0 0,1 12,14.7A1.3,1.3 0 0,1 13.3,16A1.3,1.3 0 0,1 12,17.3M15.73,3H8.27L3,8.27V15.73L8.27,21H15.73L21,15.73V8.27L15.73,3Z"/>
        </svg>`,
        
        info: `<svg viewBox="0 0 24 24" fill="currentColor">
            <path d="M13,9H11V7H13M13,17H11V11H13M12,2A10,10 0 0,0 2,12A10,10 0 0,0 12,22A10,10 0 0,0 22,12A10,10 0 0,0 12,2Z"/>
        </svg>`,
        
        // Navigation
        home: `<svg viewBox="0 0 24 24" fill="currentColor">
            <path d="M10,20V14H14V20H19V12H22L12,3L2,12H5V20H10Z"/>
        </svg>`,
        
        // Others
        magic: `<svg viewBox="0 0 24 24" fill="currentColor">
            <path d="M7.5,5.6L10,7L8.6,4.5L10,2L7.5,3.4L5,2L6.4,4.5L5,7L7.5,5.6M19.5,15.4L22,14L20.6,16.5L22,19L19.5,17.6L17,19L18.4,16.5L17,14L19.5,15.4M22,2L20.6,4.5L22,7L19.5,5.6L17,7L18.4,4.5L17,2L19.5,3.4L22,2M13.34,12.78L15.78,10.34L13.66,8.22L11.22,10.66L13.34,12.78M14.37,7.29L16.71,9.63C17.1,10 17.1,10.65 16.71,11.04L5.04,22.71C4.65,23.1 4,23.1 3.63,22.71L1.29,20.37C0.9,20 0.9,19.35 1.29,18.96L12.96,7.29C13.35,6.9 14,6.9 14.37,7.29Z"/>
        </svg>`
    };
    
    /**
     * Get an SVG icon with specified size and classes
     * @param {string} name - Icon name
     * @param {number} size - Icon size in pixels
     * @param {string} classes - Additional CSS classes
     * @param {string} ariaLabel - Accessibility label
     * @returns {string} SVG HTML string
     */
    static getIcon(name, size = 24, classes = '', ariaLabel = '') {
        const icon = this.icons[name];
        if (!icon) {
            console.warn(`Icon "${name}" not found in library`);
            return this.icons.error;
        }
        
        const ariaAttrs = ariaLabel ? `aria-label="${ariaLabel}" role="img"` : 'aria-hidden="true"';
        
        return icon
            .replace('<svg', `<svg width="${size}" height="${size}" class="svg-icon ${classes}" ${ariaAttrs}`)
            .replace(/currentColor/g, 'currentColor');
    }
    
    /**
     * Create an interactive icon button element
     * @param {string} iconName - Icon name
     * @param {string} label - Button label
     * @param {Function} onClick - Click handler
     * @param {Object} options - Additional options
     * @returns {HTMLButtonElement}
     */
    static createIconButton(iconName, label, onClick, options = {}) {
        const button = document.createElement('button');
        button.type = 'button';
        button.className = `btn ${options.className || 'btn-outline-primary'}`;
        button.innerHTML = `${this.getIcon(iconName, options.size || 16)} <span class="${options.hideLabel ? 'sr-only' : 'ms-1'}">${label}</span>`;
        button.setAttribute('aria-label', label);
        
        if (options.disabled) {
            button.disabled = true;
        }
        
        if (onClick) {
            button.addEventListener('click', onClick);
        }
        
        return button;
    }
    
    /**
     * Replace all emoji in a container with SVG icons
     * @param {HTMLElement} container - Container element
     */
    static replaceEmojiWithSvg(container) {
        const emojiMap = {
            '🎬': 'video',
            '🎥': 'video',
            '🖼️': 'image',
            '📸': 'image',
            '🎵': 'audio',
            '🎤': 'audio',
            '📄': 'document',
            '🗜️': 'archive',
            '📁': 'batch',
            '⚡': 'batch',
            '🏠': 'home',
            '🔧': 'settings',
            '🔄': 'convert',
            '▶️': 'play',
            '⏸️': 'pause',
            '📥': 'upload',
            '📤': 'download',
            '✨': 'magic'
        };
        
        const walker = document.createTreeWalker(
            container,
            NodeFilter.SHOW_TEXT,
            null,
            false
        );
        
        const textNodes = [];
        let node;
        while (node = walker.nextNode()) {
            textNodes.push(node);
        }
        
        textNodes.forEach(textNode => {
            let hasReplacement = false;
            let newHTML = textNode.textContent;
            
            Object.entries(emojiMap).forEach(([emoji, iconName]) => {
                if (newHTML.includes(emoji)) {
                    const icon = this.getIcon(iconName, 24, '', emoji);
                    newHTML = newHTML.replace(new RegExp(emoji, 'g'), icon);
                    hasReplacement = true;
                }
            });
            
            if (hasReplacement && textNode.parentNode) {
                const wrapper = document.createElement('span');
                wrapper.innerHTML = newHTML;
                textNode.parentNode.replaceChild(wrapper, textNode);
            }
        });
    }
    
    /**
     * Initialize icon animations and interactions
     */
    static initializeAnimations() {
        // Add hover effects to all SVG icons
        const style = document.createElement('style');
        style.textContent = `
            .svg-icon {
                transition: transform 0.2s ease, opacity 0.2s ease;
            }
            
            .svg-icon:hover {
                transform: scale(1.1);
            }
            
            .btn .svg-icon {
                transition: all 0.2s ease;
            }
            
            .btn:hover .svg-icon {
                transform: translateY(-1px);
            }
            
            .svg-icon.spin {
                animation: icon-spin 1s linear infinite;
            }
            
            .svg-icon.pulse {
                animation: icon-pulse 2s ease-in-out infinite;
            }
            
            @keyframes icon-spin {
                from { transform: rotate(0deg); }
                to { transform: rotate(360deg); }
            }
            
            @keyframes icon-pulse {
                0%, 100% { opacity: 1; }
                50% { opacity: 0.5; }
            }
            
            .file-type-icon .svg-icon {
                filter: drop-shadow(0 2px 4px rgba(0, 0, 0, 0.1));
            }
            
            @media (prefers-reduced-motion: reduce) {
                .svg-icon,
                .svg-icon:hover,
                .btn:hover .svg-icon {
                    transform: none;
                    transition: none;
                }
                
                .svg-icon.spin,
                .svg-icon.pulse {
                    animation: none;
                }
            }
        `;
        document.head.appendChild(style);
    }
}

// Auto-initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    IconLibrary.initializeAnimations();
    
    // Replace emoji with SVG icons in existing content
    setTimeout(() => {
        IconLibrary.replaceEmojiWithSvg(document.body);
    }, 100);
});

// Make available globally
window.IconLibrary = IconLibrary;
