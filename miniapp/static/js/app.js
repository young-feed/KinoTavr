// Telegram WebApp SDK initialization
const tg = window.Telegram.WebApp;
tg.expand();
tg.enableClosingConfirmation();

// State management
let userHistory = [];
let conversationHistory = [];
let lastQuestion = '';
let currentGradient = { start: '#2481cc', end: '#1a5a8a' };
let lastColor = null;
let favoriteMovies = [];
let isLoadingMore = false;

// DOM elements
const chatContainer = document.getElementById('chatContainer');
const historyContainer = document.getElementById('historyContainer');
const messageInput = document.getElementById('messageInput');
const sendBtn = document.getElementById('sendBtn');
const historyBtn = document.getElementById('historyBtn');
const resetBtn = document.getElementById('resetBtn');
const backBtn = document.getElementById('backBtn');
const chatView = document.getElementById('chatView');
const historyView = document.getElementById('historyView');

let currentHistoryTab = 'all';

// API URL from environment or default
const API_URL = 'API_URL_PLACEHOLDER';

// Color mapping from backend color names to hex codes
const COLOR_MAP = {
    'deep_blue': '#1e3a8a',
    'yellow': '#fbbf24',
    'crimson': '#dc2626',
    'black': '#1a1a1a',
    'purple': '#9333ea',
    'emerald': '#059669'
};

// Initialize
init();

function init() {
    loadHistory();
    loadConversation();
    loadFavorites();
    setupEventListeners();
    applyTelegramTheme();

    // Remove welcome message if there's conversation history
    if (conversationHistory.length > 0) {
        document.querySelector('.welcome-message')?.remove();
        renderConversation();
    }
}

function setupEventListeners() {
    messageInput.addEventListener('input', handleInputChange);
    messageInput.addEventListener('keydown', handleKeyDown);
    sendBtn.addEventListener('click', sendMessage);
    historyBtn.addEventListener('click', showHistory);
    backBtn.addEventListener('click', hideHistory);
    resetBtn.addEventListener('click', resetDialog);

    // History tabs
    document.querySelectorAll('.history-tab').forEach(tab => {
        tab.addEventListener('click', () => {
            try {
                tg.HapticFeedback.impactOccurred('light');
            } catch (e) {
                console.log('Haptic feedback not available');
            }

            document.querySelectorAll('.history-tab').forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            currentHistoryTab = tab.dataset.tab;
            renderHistory();
        });
    });
}

function handleInputChange() {
    const value = messageInput.value.trim();
    sendBtn.disabled = !value;

    // Auto-resize textarea
    messageInput.style.height = 'auto';
    messageInput.style.height = messageInput.scrollHeight + 'px';
}

// Debounce function for optimization
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

function handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        if (!sendBtn.disabled) {
            sendMessage();
        }
    }
}

async function sendMessage() {
    const text = messageInput.value.trim();
    if (!text) return;

    // Haptic feedback on send
    try {
        tg.HapticFeedback.impactOccurred('light');
    } catch (e) {
        console.log('Haptic feedback not available');
    }

    // Remove welcome message if it exists
    document.querySelector('.welcome-message')?.remove();

    // Add user message to UI
    addMessage(text, 'user');

    // Clear input
    messageInput.value = '';
    messageInput.style.height = 'auto';
    sendBtn.disabled = true;

    // Add to conversation history
    conversationHistory.push({
        question: lastQuestion,
        answer: text
    });

    // Save conversation to localStorage
    saveConversation();

    // Show typing indicator (replaced with skeleton on movie response)
    const typingIndicator = addTypingIndicator();

    // Send to backend
    try {
        const response = await fetch(API_URL, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                user_id: tg.initDataUnsafe?.user?.id || 'webapp_user',
                consversion: conversationHistory
            })
        });

        const data = await response.json();

        // Remove typing indicator
        typingIndicator.remove();

        handleBackendResponse(data);

    } catch (error) {
        console.error('Error:', error);
        typingIndicator.remove();
        addMessage('Произошла ошибка при подключении к серверу. Попробуйте еще раз.', 'bot');
        tg.showAlert('Ошибка подключения к серверу');
    }
}

function handleBackendResponse(data) {
    const { action, text, movie, color } = data;

    // Update gradient if color is provided (for both ask and recommend actions)
    if (color) {
        updateGradient(color);
        lastColor = color;
    }

    if (action === 'ask') {
        // Bot asks another question
        addMessage(text, 'bot');
        lastQuestion = text;

    } else if (action === 'recommend') {
        // Haptic feedback for success
        try {
            tg.HapticFeedback.notificationOccurred('success');
        } catch (e) {
            console.log('Haptic feedback not available');
        }

        // Bot recommends a movie
        addMessage(text, 'bot');

        if (movie) {
            addMovieCard(movie);
            saveToHistory(movie, color);
        }

        // Reset conversation after recommendation
        setTimeout(() => {
            conversationHistory = [];
            lastQuestion = '';
            saveConversation();
        }, 1000);

    } else {
        // Error or other action
        addMessage(text || 'Что-то пошло не так. Попробуйте еще раз.', 'bot');
    }
}

function addMessage(text, type) {
    const messageEl = document.createElement('div');
    messageEl.className = `message ${type}`;

    const bubbleEl = document.createElement('div');
    bubbleEl.className = 'message-bubble';
    bubbleEl.textContent = text;

    messageEl.appendChild(bubbleEl);
    chatContainer.appendChild(messageEl);

    scrollToBottom();
}

function addMovieCard(movie) {
    const cardEl = document.createElement('div');
    cardEl.className = 'message bot';

    const movieCard = document.createElement('div');
    movieCard.className = 'movie-card';

    const titleEl = document.createElement('div');
    titleEl.className = 'movie-title';
    titleEl.textContent = `🍿 ${movie.title}`;

    if (movie.year) {
        const yearEl = document.createElement('span');
        yearEl.className = 'movie-year';
        yearEl.textContent = ` (${movie.year})`;
        titleEl.appendChild(yearEl);
    }

    movieCard.appendChild(titleEl);

    if (movie.description) {
        const descEl = document.createElement('div');
        descEl.className = 'movie-description';
        descEl.textContent = movie.description;
        movieCard.appendChild(descEl);
    }

    // Add links and favorite button
    const actionsEl = document.createElement('div');
    actionsEl.className = 'movie-actions';

    // Favorite button
    const isFavorite = favoriteMovies.some(fav => fav.id === movie.id || fav.title === movie.title);
    const favoriteBtn = document.createElement('button');
    favoriteBtn.className = `favorite-btn ${isFavorite ? 'active' : ''}`;
    favoriteBtn.innerHTML = isFavorite ? '⭐' : '☆';
    favoriteBtn.onclick = () => toggleFavorite(movie, favoriteBtn);
    actionsEl.appendChild(favoriteBtn);

    // Links
    const links = [];
    if (movie.kp_url) {
        links.push(`<a href="${movie.kp_url}" class="movie-link" target="_blank">Кинопоиск</a>`);
    }
    if (movie.rutube_url) {
        links.push(`<a href="${movie.rutube_url}" class="movie-link" target="_blank">Смотреть на Rutube</a>`);
    }

    if (links.length > 0) {
        const linksEl = document.createElement('div');
        linksEl.className = 'movie-links';
        linksEl.innerHTML = links.join('');
        actionsEl.appendChild(linksEl);
    }

    movieCard.appendChild(actionsEl);

    cardEl.appendChild(movieCard);
    chatContainer.appendChild(cardEl);

    scrollToBottom();
}

function addTypingIndicator() {
    const typingEl = document.createElement('div');
    typingEl.className = 'message bot';
    typingEl.id = 'typingIndicator';

    const indicator = document.createElement('div');
    indicator.className = 'typing-indicator';
    indicator.innerHTML = '<div class="typing-dot"></div><div class="typing-dot"></div><div class="typing-dot"></div>';

    typingEl.appendChild(indicator);
    chatContainer.appendChild(typingEl);

    scrollToBottom();

    return typingEl;
}

function addSkeletonLoader() {
    const skeletonEl = document.createElement('div');
    skeletonEl.className = 'message bot';
    skeletonEl.id = 'skeletonLoader';

    const skeleton = document.createElement('div');
    skeleton.className = 'movie-card skeleton';
    skeleton.innerHTML = `
        <div class="skeleton-title"></div>
        <div class="skeleton-line"></div>
        <div class="skeleton-line"></div>
        <div class="skeleton-line short"></div>
    `;

    skeletonEl.appendChild(skeleton);
    chatContainer.appendChild(skeletonEl);

    scrollToBottom();

    return skeletonEl;
}

function scrollToBottom() {
    chatContainer.scrollTop = chatContainer.scrollHeight;
}

function updateGradient(color) {
    // Convert color name to hex if needed
    const hexColor = COLOR_MAP[color] || color;

    // Validate hex format
    if (!/^#[0-9A-Fa-f]{6}$/.test(hexColor)) {
        console.warn('Invalid color format:', color, hexColor);
        return;
    }

    // Parse color and create gradient
    const startColor = hexColor;
    const endColor = darkenColor(hexColor, 20);

    currentGradient = { start: startColor, end: endColor };

    document.documentElement.style.setProperty('--gradient-start', startColor);
    document.documentElement.style.setProperty('--gradient-end', endColor);
    document.body.style.background = `linear-gradient(135deg, ${startColor} 0%, ${endColor} 100%)`;
}

function darkenColor(color, percent) {
    // Convert hex to RGB
    let r = parseInt(color.slice(1, 3), 16);
    let g = parseInt(color.slice(3, 5), 16);
    let b = parseInt(color.slice(5, 7), 16);

    // Darken
    r = Math.floor(r * (100 - percent) / 100);
    g = Math.floor(g * (100 - percent) / 100);
    b = Math.floor(b * (100 - percent) / 100);

    // Convert back to hex
    return `#${r.toString(16).padStart(2, '0')}${g.toString(16).padStart(2, '0')}${b.toString(16).padStart(2, '0')}`;
}

function saveToHistory(movie, color) {
    userHistory.unshift({
        ...movie,
        color: color || lastColor,
        timestamp: Date.now()
    });

    // Keep only last 50 movies
    if (userHistory.length > 50) {
        userHistory = userHistory.slice(0, 50);
    }

    localStorage.setItem('movieHistory', JSON.stringify(userHistory));
}

function loadHistory() {
    try {
        const saved = localStorage.getItem('movieHistory');
        if (saved) {
            userHistory = JSON.parse(saved);
        }
    } catch (e) {
        console.error('Error loading history:', e);
    }
}

function loadConversation() {
    try {
        const saved = localStorage.getItem('conversationHistory');
        if (saved) {
            const data = JSON.parse(saved);
            conversationHistory = data.history || [];
            lastQuestion = data.lastQuestion || '';
        }
    } catch (e) {
        console.error('Error loading conversation:', e);
    }
}

function saveConversation() {
    try {
        localStorage.setItem('conversationHistory', JSON.stringify({
            history: conversationHistory,
            lastQuestion: lastQuestion
        }));
    } catch (e) {
        console.error('Error saving conversation:', e);
    }
}

function loadFavorites() {
    try {
        const saved = localStorage.getItem('favoriteMovies');
        if (saved) {
            favoriteMovies = JSON.parse(saved);
        }
    } catch (e) {
        console.error('Error loading favorites:', e);
    }
}

function saveFavorites() {
    try {
        localStorage.setItem('favoriteMovies', JSON.stringify(favoriteMovies));
    } catch (e) {
        console.error('Error saving favorites:', e);
    }
}

function toggleFavorite(movie, button) {
    try {
        tg.HapticFeedback.impactOccurred('medium');
    } catch (e) {
        console.log('Haptic feedback not available');
    }

    const index = favoriteMovies.findIndex(fav => fav.id === movie.id || fav.title === movie.title);

    if (index > -1) {
        // Remove from favorites
        favoriteMovies.splice(index, 1);
        button.classList.remove('active');
        button.innerHTML = '☆';
    } else {
        // Add to favorites
        favoriteMovies.push({
            ...movie,
            favoritedAt: Date.now()
        });
        button.classList.add('active');
        button.innerHTML = '⭐';
    }

    saveFavorites();

    // Update all favorite buttons for this movie
    updateAllFavoriteButtons(movie);
}

function updateAllFavoriteButtons(movie) {
    const isFavorite = favoriteMovies.some(fav => fav.id === movie.id || fav.title === movie.title);
    const icon = isFavorite ? '⭐' : '☆';

    // Update buttons in history
    document.querySelectorAll('.favorite-btn-small').forEach(btn => {
        try {
            const btnMovie = JSON.parse(btn.dataset.movie);
            if (btnMovie.id === movie.id || btnMovie.title === movie.title) {
                btn.innerHTML = icon;
                if (isFavorite) {
                    btn.classList.add('active');
                } else {
                    btn.classList.remove('active');
                }
            }
        } catch (e) {
            // Skip if can't parse
        }
    });
}

function showHistory() {
    historyView.classList.add('active');

    // Apply gradient from the last movie in history
    if (userHistory.length > 0 && userHistory[0].color) {
        const colorName = userHistory[0].color;
        const historyColor = COLOR_MAP[colorName] || colorName;

        // Validate hex format before applying
        if (/^#[0-9A-Fa-f]{6}$/.test(historyColor)) {
            const historyGradientEnd = darkenColor(historyColor, 20);
            historyView.style.background = `linear-gradient(135deg, ${historyColor} 0%, ${historyGradientEnd} 100%)`;
        }
    }

    renderHistory();
}

function hideHistory() {
    historyView.classList.remove('active');
}

function renderHistory() {
    const moviesToShow = currentHistoryTab === 'favorites' ? favoriteMovies : userHistory;

    if (moviesToShow.length === 0) {
        const emptyIcon = currentHistoryTab === 'favorites' ? '⭐' : '📽️';
        const emptyText = currentHistoryTab === 'favorites' ? 'Избранное пусто' : 'История пока пуста';
        const emptyHint = currentHistoryTab === 'favorites'
            ? 'Добавляйте фильмы в избранное нажав на звездочку'
            : 'Найденные фильмы будут отображаться здесь';

        historyContainer.innerHTML = `
            <div class="empty-history">
                <div class="empty-icon">${emptyIcon}</div>
                <p>${emptyText}</p>
                <span>${emptyHint}</span>
            </div>
        `;
        return;
    }

    historyContainer.innerHTML = '';

    moviesToShow.forEach(movie => {
        const itemEl = document.createElement('div');
        itemEl.className = 'history-item';

        const isFavorite = favoriteMovies.some(fav => fav.id === movie.id || fav.title === movie.title);

        itemEl.innerHTML = `
            <div class="history-item-header">
                <div class="history-item-title">${movie.title}</div>
                <button class="favorite-btn-small ${isFavorite ? 'active' : ''}" data-movie='${JSON.stringify(movie).replace(/'/g, "&apos;")}'>
                    ${isFavorite ? '⭐' : '☆'}
                </button>
            </div>
            ${movie.year ? `<div class="history-item-year">${movie.year}</div>` : ''}
            ${movie.description ? `<div class="history-item-description">${movie.description}</div>` : ''}
        `;

        // Add favorite button handler
        const favBtn = itemEl.querySelector('.favorite-btn-small');
        favBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            const movieData = JSON.parse(favBtn.dataset.movie);
            toggleFavorite(movieData, favBtn);

            // If we're on favorites tab and removing, re-render
            if (currentHistoryTab === 'favorites') {
                renderHistory();
            }
        });

        itemEl.addEventListener('click', () => {
            const links = [];
            if (movie.kp_url) links.push(movie.kp_url);
            if (movie.rutube_url) links.push(movie.rutube_url);

            if (links.length > 0) {
                tg.openLink(links[0]);
            }
        });

        historyContainer.appendChild(itemEl);
    });
}

function resetDialog() {
    tg.showConfirm('Начать новый диалог? Текущая беседа будет очищена.', (confirmed) => {
        if (confirmed) {
            conversationHistory = [];
            lastQuestion = '';
            saveConversation();

            chatContainer.innerHTML = `
                <div class="welcome-message">
                    <img src="/static/logo.svg" alt="Кинотавр" class="bot-logo">
                    <h2>Привет! Я Кинотавр</h2>
                    <p>Расскажи, какое у тебя сейчас настроение, или чего хочется от фильма на вечер?</p>
                </div>
            `;

            // Reset gradient to default
            updateGradient('#2481cc');

            try {
                tg.HapticFeedback.notificationOccurred('success');
            } catch (e) {
                console.log('Haptic feedback not available');
            }

            tg.showPopup({
                message: 'Диалог сброшен. Можете начать заново!'
            });
        }
    });
}

function renderConversation() {
    chatContainer.innerHTML = '';

    conversationHistory.forEach(item => {
        if (item.question) {
            addMessage(item.question, 'bot');
        }
        if (item.answer) {
            addMessage(item.answer, 'user');
        }
    });
}

function applyTelegramTheme() {
    // Apply Telegram theme colors if available
    if (tg.themeParams) {
        const params = tg.themeParams;

        if (params.bg_color) {
            document.documentElement.style.setProperty('--tg-theme-bg-color', params.bg_color);
        }
        if (params.text_color) {
            document.documentElement.style.setProperty('--tg-theme-text-color', params.text_color);
        }
        if (params.hint_color) {
            document.documentElement.style.setProperty('--tg-theme-hint-color', params.hint_color);
        }
        if (params.link_color) {
            document.documentElement.style.setProperty('--tg-theme-link-color', params.link_color);
        }
        if (params.button_color) {
            document.documentElement.style.setProperty('--tg-theme-button-color', params.button_color);
        }
        if (params.button_text_color) {
            document.documentElement.style.setProperty('--tg-theme-button-text-color', params.button_text_color);
        }
        if (params.secondary_bg_color) {
            document.documentElement.style.setProperty('--tg-theme-secondary-bg-color', params.secondary_bg_color);
        }
    }
}
