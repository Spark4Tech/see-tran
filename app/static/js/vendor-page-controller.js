// vendor-page-controller.js - Add this to the vendors.html template

// =============================================================================
// VENDOR PAGE STATE MANAGEMENT
// =============================================================================

class VendorPageController {
  constructor() {
    this.currentFilters = {
      search: '',
      agency: '',
      functional_area: '',
      sort: 'name'
    };
    this.selectedVendorId = null;
    this.isLoading = false;
    this.refreshTimers = [];
    
    this.init();
  }

  /**
   * Initialize the vendor page controller
   */
  init() {
    this.setupEventListeners();
    this.loadInitialData();
    this.setupPeriodicRefresh();
    console.log('🏢 Vendor page controller initialized');
  }

  /**
   * Setup all event listeners
   */
  setupEventListeners() {
    // Filter form changes
    const form = document.getElementById('vendor-filters');
    if (form) {
      form.addEventListener('input', this.handleFilterChange.bind(this));
      form.addEventListener('change', this.handleFilterChange.bind(this));
    }

    // HTMX event listeners
    document.body.addEventListener('htmx:beforeRequest', this.handleBeforeRequest.bind(this));
    document.body.addEventListener('htmx:afterRequest', this.handleAfterRequest.bind(this));
    document.body.addEventListener('htmx:afterSwap', this.handleAfterSwap.bind(this));
    document.body.addEventListener('htmx:responseError', this.handleResponseError.bind(this));

    // Custom events for vendor operations
    document.addEventListener('vendor:created', this.handleVendorCreated.bind(this));
    document.addEventListener('vendor:updated', this.handleVendorUpdated.bind(this));
    document.addEventListener('vendor:deleted', this.handleVendorDeleted.bind(this));
  }

  /**
   * Load initial page data
   */
  async loadInitialData() {
    try {
      // Load filter options
      await Promise.all([
        this.loadFilterOptions(),
        this.loadVendorStats(),
        this.loadVendorPerformance()
      ]);
    } catch (error) {
      console.error('Error loading initial data:', error);
      showToast('Error loading page data. Please refresh.', false);
    }
  }

  /**
   * Load filter dropdown options
   */
  async loadFilterOptions() {
    try {
      // Load agency options
      const agencyResponse = await fetch('/api/vendors/filter-options/agencies');
      const agencyHtml = await agencyResponse.text();
      const agencySelect = document.getElementById('agency-filter');
      if (agencySelect) {
        agencySelect.innerHTML = agencyHtml;
      }

      // Load functional area options
      const faResponse = await fetch('/api/vendors/filter-options/functional-areas');
      const faHtml = await faResponse.text();
      const faSelect = document.getElementById('functional-area-filter');
      if (faSelect) {
        faSelect.innerHTML = faHtml;
      }
    } catch (error) {
      console.error('Error loading filter options:', error);
    }
  }

  /**
   * Handle filter changes with debouncing
   */
  handleFilterChange(event) {
    const formData = new FormData(document.getElementById('vendor-filters'));
    const newFilters = {};
    
    for (const [key, value] of formData.entries()) {
      newFilters[key] = value.trim();
    }

    // Update current filters
    this.currentFilters = { ...this.currentFilters, ...newFilters };

    // Debounce search input
    if (event.target.name === 'search') {
      clearTimeout(this.searchTimeout);
      this.searchTimeout = setTimeout(() => {
        this.refreshVendorList();
        this.updateActiveFilters();
      }, 300);
    } else {
      // Immediate update for dropdowns
      this.refreshVendorList();
      this.updateActiveFilters();
    }

    // Update stats and performance with current filters
    this.loadVendorStats();
    this.loadVendorPerformance();
  }

  /**
   * Refresh vendor list while preserving state
   */
  refreshVendorList() {
    if (this.isLoading) return;
    
    const vendorsList = document.getElementById('vendors-list');
    if (vendorsList) {
      // Show loading state
      this.showListLoading(true);
      
      // Trigger HTMX refresh with current filters
      htmx.trigger(vendorsList, 'refresh');
    }
  }

  /**
   * Update active filter badges
   */
  updateActiveFilters() {
    const filterContainer = document.getElementById('active-filters');
    const clearBtn = document.getElementById('clear-filters-btn');
    
    if (!filterContainer) return;
    
    filterContainer.innerHTML = '';
    let hasActiveFilters = false;
    
    // Create filter badges
    Object.entries(this.currentFilters).forEach(([key, value]) => {
      if (value && value !== '' && key !== 'sort') {
        hasActiveFilters = true;
        
        let displayKey = key;
        if (key === 'functional_area') displayKey = 'functional area';
        
        const badge = document.createElement('span');
        badge.className = 'inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-purple-600/20 text-purple-300 border border-purple-600/30';
        badge.innerHTML = `
          ${displayKey}: ${value}
          <button onclick="vendorController.clearSpecificFilter('${key}')" class="ml-1 text-purple-400 hover:text-purple-200 transition-colors">
            <svg class="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
              <path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd"/>
            </svg>
          </button>
        `;
        filterContainer.appendChild(badge);
      }
    });
    
    // Show/hide clear all button
    if (clearBtn) {
      clearBtn.style.display = hasActiveFilters ? 'inline-block' : 'none';
    }
  }

  /**
   * Clear specific filter
   */
  clearSpecificFilter(filterKey) {
    const form = document.getElementById('vendor-filters');
    if (form) {
      const element = form.querySelector(`[name="${filterKey}"]`);
      if (element) {
        element.value = '';
        this.currentFilters[filterKey] = '';
        
        // Trigger refresh
        this.refreshVendorList();
        this.updateActiveFilters();
        this.loadVendorStats();
        this.loadVendorPerformance();
      }
    }
  }

  /**
   * Clear all filters
   */
  clearAllFilters() {
    const form = document.getElementById('vendor-filters');
    if (form) {
      // Reset form elements
      form.reset();
      
      // Reset current filters
      this.currentFilters = {
        search: '',
        agency: '',
        functional_area: '',
        sort: 'name'
      };
      
      // Update UI
      this.refreshVendorList();
      this.updateActiveFilters();
      this.loadVendorStats();
      this.loadVendorPerformance();
    }
  }

  /**
   * Load vendor statistics with current filters
   */
  async loadVendorStats() {
    try {
      const params = new URLSearchParams();
      Object.entries(this.currentFilters).forEach(([key, value]) => {
        if (value && value.trim() !== '') {
          params.append(key, value.trim());
        }
      });
      
      const response = await fetch('/api/vendors/stats?' + params.toString());
      const data = await response.json();
      
      if (data.status !== 'error') {
        document.getElementById('active-vendors-count').textContent = data.active_vendors;
        document.getElementById('avg-systems-count').textContent = data.avg_components_per_vendor;
        
        if (data.top_vendor) {
          document.getElementById('top-vendor-count').textContent = data.top_vendor.component_count;
        }
      }
    } catch (error) {
      console.error('Error loading vendor stats:', error);
    }
  }

  /**
   * Load vendor performance insights with current filters
   */
  async loadVendorPerformance() {
    try {
      const params = new URLSearchParams();
      Object.entries(this.currentFilters).forEach(([key, value]) => {
        if (value && value.trim() !== '') {
          params.append(key, value.trim());
        }
      });
      
      const response = await fetch('/api/vendors/performance?' + params.toString());
      const data = await response.json();
      
      if (data.status !== 'error') {
        document.getElementById('most-reliable-vendor').textContent = data.most_reliable;
        document.getElementById('newest-vendor').textContent = data.newest;
        document.getElementById('largest-vendor').textContent = data.largest;
      }
    } catch (error) {
      console.error('Error loading vendor performance:', error);
    }
  }

  /**
   * Show/hide loading state for vendor list
   */
  showListLoading(show) {
    const vendorsList = document.getElementById('vendors-list');
    if (!vendorsList) return;
    
    if (show) {
      vendorsList.style.opacity = '0.6';
      vendorsList.style.pointerEvents = 'none';
    } else {
      vendorsList.style.opacity = '1';
      vendorsList.style.pointerEvents = 'auto';
    }
  }

  /**
   * Update vendor count display
   */
  updateVendorCount() {
    const metaElement = document.getElementById('vendor-list-meta');
    const countDisplay = document.getElementById('vendor-count-display');
    
    if (metaElement && countDisplay) {
      const count = parseInt(metaElement.dataset.count) || 0;
      countDisplay.textContent = `${count} vendor${count !== 1 ? 's' : ''} found`;
    }
  }

  /**
   * Setup periodic refresh for stats
   */
  setupPeriodicRefresh() {
    // Refresh stats every 30 seconds
    this.refreshTimers.push(
      setInterval(() => {
        const elements = document.querySelectorAll('[hx-get*="/api/count/"]');
        elements.forEach(el => htmx.trigger(el, 'refresh'));
      }, 30000)
    );
  }

  /**
   * Handle HTMX before request
   */
  handleBeforeRequest(event) {
    const target = event.target;
    
    if (target.id === 'vendors-list') {
      this.isLoading = true;
      this.showListLoading(true);
    }
  }

  /**
   * Handle HTMX after request
   */
  handleAfterRequest(event) {
    const target = event.target;
    
    if (target.id === 'vendors-list') {
      this.isLoading = false;
      this.showListLoading(false);
    }
  }

  /**
   * Handle HTMX after swap
   */
  handleAfterSwap(event) {
    const target = event.target;
    
    if (target.id === 'vendors-list') {
      // Update vendor count
      setTimeout(() => this.updateVendorCount(), 100);
      
      // Add hover effects to vendor cards
      this.setupVendorCardEffects();
      
      // Restore selected vendor state if needed
      if (this.selectedVendorId) {
        this.highlightSelectedVendor(this.selectedVendorId);
      }
    }
  }

  /**
   * Handle HTMX response errors
   */
  handleResponseError(event) {
    if (event.target.id === 'vendors-list') {
      this.isLoading = false;
      this.showListLoading(false);
      showToast('Error loading vendors. Please try again.', false);
    }
  }

  /**
   * Setup hover effects for vendor cards
   */
  setupVendorCardEffects() {
    const vendorCards = document.querySelectorAll('.vendor-card');
    vendorCards.forEach(card => {
      // Remove existing listeners to prevent duplicates
      card.removeEventListener('mouseenter', this.cardHoverIn);
      card.removeEventListener('mouseleave', this.cardHoverOut);
      
      // Add hover effects
      card.addEventListener('mouseenter', this.cardHoverIn);
      card.addEventListener('mouseleave', this.cardHoverOut);
      
      // Track selection
      card.addEventListener('click', (e) => {
        if (!e.target.closest('a') && !e.target.closest('button')) {
          this.selectedVendorId = card.dataset.vendorId;
          this.highlightSelectedVendor(this.selectedVendorId);
        }
      });
    });
  }

  /**
   * Card hover in effect
   */
  cardHoverIn(e) {
    e.currentTarget.style.transform = 'translateY(-4px)';
    e.currentTarget.style.boxShadow = '0 10px 25px rgba(0, 0, 0, 0.3)';
  }

  /**
   * Card hover out effect
   */
  cardHoverOut(e) {
    if (!e.currentTarget.classList.contains('selected')) {
      e.currentTarget.style.transform = 'translateY(0)';
      e.currentTarget.style.boxShadow = 'none';
    }
  }

  /**
   * Highlight selected vendor card
   */
  highlightSelectedVendor(vendorId) {
    // Remove previous selection
    document.querySelectorAll('.vendor-card').forEach(card => {
      card.classList.remove('selected');
      if (!card.matches(':hover')) {
        card.style.transform = 'translateY(0)';
        card.style.boxShadow = 'none';
      }
    });
    
    // Highlight new selection
    const selectedCard = document.querySelector(`[data-vendor-id="${vendorId}"]`);
    if (selectedCard) {
      selectedCard.classList.add('selected');
      selectedCard.style.transform = 'translateY(-4px)';
      selectedCard.style.boxShadow = '0 10px 25px rgba(147, 51, 234, 0.3)';
    }
  }

  /**
   * Handle vendor created event
   */
  handleVendorCreated(event) {
    // Refresh the vendor list
    this.refreshVendorList();
    
    // Reload stats and performance
    this.loadVendorStats();
    this.loadVendorPerformance();
    
    // Close any open forms
    this.closeVendorDetails();
    
    console.log('Vendor created:', event.detail);
  }

  /**
   * Handle vendor updated event
   */
  handleVendorUpdated(event) {
    // Refresh the vendor list
    this.refreshVendorList();
    
    // Reload stats and performance
    this.loadVendorStats();
    this.loadVendorPerformance();
    
    // Keep the vendor selected if it was being edited
    if (event.detail && event.detail.vendorId) {
      this.selectedVendorId = event.detail.vendorId;
      
      // Reload vendor details after list refresh
      setTimeout(() => {
        htmx.ajax('GET', `/api/vendors/${event.detail.vendorId}/details`, {
          target: '#vendor-details',
          swap: 'innerHTML'
        });
      }, 500);
    }
    
    console.log('Vendor updated:', event.detail);
  }

  /**
   * Handle vendor deleted event
   */
  handleVendorDeleted(event) {
    // Clear selection if the deleted vendor was selected
    if (event.detail && event.detail.vendorId === this.selectedVendorId) {
      this.selectedVendorId = null;
      this.closeVendorDetails();
    }
    
    // Refresh the vendor list
    this.refreshVendorList();
    
    // Reload stats and performance
    this.loadVendorStats();
    this.loadVendorPerformance();
    
    console.log('Vendor deleted:', event.detail);
  }

  /**
   * Close vendor details panel
   */
  closeVendorDetails() {
    this.selectedVendorId = null;
    
    document.getElementById('vendor-details').innerHTML = `
      <div class="glass-effect rounded-xl p-6 border border-slate-700/50 text-center">
        <div class="w-16 h-16 bg-slate-700 rounded-full flex items-center justify-center mx-auto mb-4">
          <svg class="w-8 h-8 text-slate-500" fill="currentColor" viewBox="0 0 20 20">
            <path d="M13 6a3 3 0 11-6 0 3 3 0 016 0zM18 8a2 2 0 11-4 0 2 2 0 014 0zM14 15a4 4 0 00-8 0v3h8v-3z"/>
          </svg>
        </div>
        <h3 class="text-lg font-medium text-slate-400 mb-2">Vendor Details</h3>
        <p class="text-slate-500 text-sm">Click on a vendor to view detailed information, system portfolio, and contact details.</p>
      </div>`;
  }

  /**
   * Optimistic update for vendor creation
   */
  optimisticCreateVendor(vendorData) {
    // Add temporary vendor card with loading state
    const vendorsList = document.getElementById('vendors-list');
    if (vendorsList && !vendorsList.querySelector('.optimistic-vendor')) {
      const tempCard = document.createElement('div');
      tempCard.className = 'optimistic-vendor vendor-card bg-slate-800/30 rounded-lg border border-purple-500/50 p-6 animate-pulse';
      tempCard.innerHTML = `
        <div class="flex items-start justify-between mb-4">
          <div class="flex items-start space-x-4 flex-1">
            <div class="w-12 h-12 bg-gradient-to-r from-purple-500 to-pink-500 rounded-lg flex items-center justify-center">
              <span class="text-lg font-bold text-white">${vendorData.name[0].upper()}</span>
            </div>
            <div class="flex-1">
              <h3 class="font-semibold text-white text-lg">${vendorData.name}</h3>
              <p class="text-slate-400 text-sm">Creating vendor...</p>
            </div>
          </div>
          <div class="w-12 h-12 bg-gradient-to-r from-purple-500 to-pink-500 rounded-full flex items-center justify-center">
            <svg class="w-4 h-4 text-white animate-spin" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
          </div>
        </div>
      `;
      vendorsList.insertBefore(tempCard, vendorsList.firstChild);
    }
  }

  /**
   * Remove optimistic vendor card
   */
  removeOptimisticVendor() {
    const optimisticCard = document.querySelector('.optimistic-vendor');
    if (optimisticCard) {
      optimisticCard.remove();
    }
  }

  /**
   * Preserve scroll position during list updates
   */
  preserveScrollPosition() {
    const vendorsList = document.getElementById('vendors-list');
    if (vendorsList) {
      this.scrollPosition = vendorsList.scrollTop;
    }
  }

  /**
   * Restore scroll position after list updates
   */
  restoreScrollPosition() {
    if (this.scrollPosition !== undefined) {
      const vendorsList = document.getElementById('vendors-list');
      if (vendorsList) {
        setTimeout(() => {
          vendorsList.scrollTop = this.scrollPosition;
        }, 100);
      }
    }
  }

  /**
   * Export current vendor list (placeholder for future implementation)
   */
  exportVendorList() {
    const currentParams = new URLSearchParams();
    Object.entries(this.currentFilters).forEach(([key, value]) => {
      if (value && value.trim() !== '') {
        currentParams.append(key, value.trim());
      }
    });
    
    // For now, just show a toast with the filter parameters
    showToast(`Export functionality coming soon. Current filters: ${currentParams.toString() || 'none'}`, true);
  }

  /**
   * Cleanup method
   */
  destroy() {
    // Clear all timers
    this.refreshTimers.forEach(timer => clearInterval(timer));
    
    // Clear search timeout
    if (this.searchTimeout) {
      clearTimeout(this.searchTimeout);
    }
    
    console.log('🏢 Vendor page controller destroyed');
  }
}

// =============================================================================
// GLOBAL FUNCTIONS FOR TEMPLATE ACCESS
// =============================================================================

/**
 * Global function to clear specific filter (called from template)
 */
function clearSpecificFilter(filterKey) {
  if (window.vendorController) {
    window.vendorController.clearSpecificFilter(filterKey);
  }
}

/**
 * Global function to clear all filters (called from template)
 */
function clearAllFilters() {
  if (window.vendorController) {
    window.vendorController.clearAllFilters();
  }
}

/**
 * Global function to export vendor list (called from template)
 */
function exportVendorList() {
  if (window.vendorController) {
    window.vendorController.exportVendorList();
  }
}

/**
 * Global function to close vendor details (called from template)
 */
function closeVendorDetails() {
  if (window.vendorController) {
    window.vendorController.closeVendorDetails();
  }
}

// =============================================================================
// INITIALIZATION
// =============================================================================

// Initialize vendor controller when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
  // Only initialize on vendor page
  if (document.getElementById('vendor-filters')) {
    window.vendorController = new VendorPageController();
    
    // Make functions globally available
    window.clearSpecificFilter = clearSpecificFilter;
    window.clearAllFilters = clearAllFilters;
    window.exportVendorList = exportVendorList;
    window.closeVendorDetails = closeVendorDetails;
  }
});

// Cleanup on page unload
window.addEventListener('beforeunload', function() {
  if (window.vendorController) {
    window.vendorController.destroy();
  }
});