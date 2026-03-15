import os
from flask import request, session, jsonify
from flask_babel import Babel, get_locale as babel_get_locale

BABEL_DEFAULT_LOCALE = 'en'
BABEL_LANGUAGES = ['en', 'de', 'tr']

SUPPORTED_LANGUAGES = {
    'en': 'English',
    'de': 'Deutsch',
    'tr': 'Türkçe'
}

def get_languages_from_dir(directory):
    """Return a list of directory names in the given directory"""
    if not os.path.exists(directory):
        return BABEL_LANGUAGES
    return [name for name in os.listdir(directory)
            if os.path.isdir(os.path.join(directory, name))]

def create_babel(app):
    """Create and initialize a Babel instance with the given Flask app"""
    app.config['BABEL_DEFAULT_LOCALE'] = BABEL_DEFAULT_LOCALE
    app.config['BABEL_TRANSLATION_DIRECTORIES'] = 'translations'
    app.config['BABEL_LANGUAGES'] = get_languages_from_dir('translations')
    
    babel = Babel(app, locale_selector=select_locale)
    
    # Context processor für Templates
    @app.context_processor
    def inject_languages():
        """Inject language info into all templates"""
        try:
            current_lang = session.get('language') or request.accept_languages.best_match(app.config['BABEL_LANGUAGES']) or BABEL_DEFAULT_LOCALE
        except:
            current_lang = BABEL_DEFAULT_LOCALE
        
        return dict(
            supported_languages=SUPPORTED_LANGUAGES,
            current_language=current_lang
        )
    
    print(f"✓ Babel 4.0.0 initialized with languages: {app.config['BABEL_LANGUAGES']}")
    return babel

def select_locale():
    """Select language based on user preference"""
    # 1. Check URL parameter
    if 'lang' in request.args:
        lang = request.args.get('lang')
        if lang in BABEL_LANGUAGES:
            session['language'] = lang
            return lang
    
    # 2. Check session
    if 'language' in session:
        lang = session['language']
        if lang in BABEL_LANGUAGES:
            return lang
    
    # 3. Check browser Accept-Language header
    lang = request.accept_languages.best_match(BABEL_LANGUAGES)
    if lang:
        return lang
    
    # 4. Default
    return BABEL_DEFAULT_LOCALE

def get_locale():
    """Get current locale as JSON response"""
    if 'language' in session:
        current = session['language']
    else:
        current = request.accept_languages.best_match(BABEL_LANGUAGES) or BABEL_DEFAULT_LOCALE
    
    return jsonify({'current_language': current})

def get_languages():
    """Get supported languages as JSON response"""
    supported = get_languages_from_dir('translations')
    
    return jsonify({
        'supported': supported,
        'names': {k: v for k, v in SUPPORTED_LANGUAGES.items() if k in supported}
    })
