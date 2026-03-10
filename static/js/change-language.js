/**
 * Auto-detect system language on page load
 */
document.addEventListener('DOMContentLoaded', initLanguage);

function initLanguage() {
    try {
        // Get browser's preferred language
        const browserLang = getBrowserLanguage();
        
        // Get current page language
        const currentLang = document.documentElement.lang || 'en';
        
        // If browser language differs from page language, change it
        if (browserLang && browserLang !== currentLang) {
            changeLanguage(browserLang);
        }
    } catch (error) {
        console.error('Language initialization failed:', error);
    }
}

/**
 * Get browser's preferred language
 */
function getBrowserLanguage() {
    // Check localStorage first
    const savedLang = localStorage.getItem('language');
    if (savedLang) return savedLang;
    
    // Get browser language (first zwei chars, z.B. 'en', 'de')
    const browserLang = navigator.language.split('-')[0];
    
    // Nur 'de' und 'en' unterstützen
    return ['de', 'en'].includes(browserLang) ? browserLang : 'en';
}

/**
 * Change language and reload page
 */
function changeLanguage(lang) {
    // Validate language
    if (!['de', 'en'].includes(lang)) {
        console.error('Unsupported language:', lang);
        return;
    }
    
    // Save to localStorage
    localStorage.setItem('language', lang);
    
    // Reload page with language parameter
    const currentUrl = new URL(window.location);
    currentUrl.searchParams.set('lang', lang);
    window.location.href = currentUrl.toString();
}
