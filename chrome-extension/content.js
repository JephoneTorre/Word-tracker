let recognition = null;
let isListening = false;
let activeCombos = {};
let wordHistory = {};
let previewCounts = {};

let persistentConfig = {
    wordCounts: {},
    gibberishCount: {},
    totalWords: 0
};

// Ignore common words
const STOPWORDS = [
    "the", "to", "a", "and", "is", "of", "in", "that", "it", "on", "i", "im"
];

// Load persistent stats from storage
chrome.storage.local.get(['wordCounts', 'gibberishCount', 'totalWords'], (res) => {
    persistentConfig.wordCounts = res.wordCounts || {};
    persistentConfig.gibberishCount = res.gibberishCount || {};
    persistentConfig.totalWords = res.totalWords || 0;
});

// Debounced save for performance
let saveTimeout = null;
function saveStats() {
    clearTimeout(saveTimeout);
    saveTimeout = setTimeout(() => {
        chrome.storage.local.set({
            wordCounts: persistentConfig.wordCounts,
            gibberishCount: persistentConfig.gibberishCount,
            totalWords: persistentConfig.totalWords
        });
    }, 1000);
}

function cleanWord(word) {
    return word.toLowerCase().replace(/[^\w]/g, "");
}

function isGibberish(word) {
    return (
        /(.)\1{2,}/.test(word) ||
        /^[uhm]+$/.test(word) ||
        /^[^aeiou]{3,}$/.test(word)
    );
}

function trackWord(word) {
    const now = Date.now();

    if (!wordHistory[word]) {
        wordHistory[word] = [];
    }

    // Add current timestamp
    wordHistory[word].push(now);

    // Keep only last 15 seconds
    wordHistory[word] = wordHistory[word].filter(
        t => now - t <= 15000
    );

    // Debug: Verify counts persist across chunks
    console.log(`Word: ${word}, Window Count: ${wordHistory[word].length}`, wordHistory[word]);

    return wordHistory[word].length;
}

function previewCombo(word) {
    previewCounts[word] = (previewCounts[word] || 0) + 1;

    if (previewCounts[word] >= 2) {
        showCombo(word, previewCounts[word]);
    }
}

function resetPreview() {
    previewCounts = {};
}

function getComboLabel(count) {
    if (count === 2) return "REPEAT";
    if (count === 3) return "REDUNDANT";
    if (count === 4) return "EXTREME";
    if (count >= 5) return "OA NAMAN NETO";
    return "";
}

function showCombo(word, count) {
    const label = getComboLabel(count);
    const text = `🔥 ${word.toUpperCase()} x${count} — ${label}`;
    const tier = Math.min(count, 5);

    if (activeCombos[word]) {
        // Update existing popup
        activeCombos[word].innerText = text;
        activeCombos[word].className = `combo-alert tier-${tier}`;

        // Add animation bump on update
        activeCombos[word].classList.add("combo-bump");
        setTimeout(() => {
            if (activeCombos[word]) activeCombos[word].classList.remove("combo-bump");
        }, 200);
        
        // Reset the auto-remove timer
        clearTimeout(activeCombos[word].timeout);
        activeCombos[word].timeout = setTimeout(() => {
            if (activeCombos[word]) {
                activeCombos[word].remove();
                delete activeCombos[word];
            }
        }, 4000);
        return;
    }

    // Create new popup
    const el = document.createElement("div");
    el.className = `combo-alert tier-${tier}`;
    el.innerText = text;

    document.body.appendChild(el);
    activeCombos[word] = el;

    // Auto-remove after delay
    el.timeout = setTimeout(() => {
        if (activeCombos[word]) {
            activeCombos[word].remove();
            delete activeCombos[word];
        }
    }, 4000);
}

function showAlert(text, color) {
    let container = document.getElementById("speech-coach-overlay");
    if (!container) {
        container = document.createElement("div");
        container.id = "speech-coach-overlay";
        document.body.appendChild(container);
    }

    const alertEl = document.createElement("div");
    alertEl.className = "speech-alert noise-alert";
    alertEl.innerHTML = `<div><strong>${text}</strong></div>`;
    alertEl.style.backgroundColor = color === 'purple' ? '#c084fc' : '#3b82f6';
    alertEl.style.color = '#fff';
    alertEl.style.padding = '8px 16px';
    alertEl.style.borderRadius = '8px';
    alertEl.style.marginBottom = '8px';
    alertEl.style.fontWeight = 'bold';
    alertEl.style.boxShadow = '0 4px 6px rgba(0, 0, 0, 0.1)';
    alertEl.style.animation = "coachSlideFadeIn 0.3s cubic-bezier(0.16, 1, 0.3, 1) forwards";
    
    container.insertBefore(alertEl, container.firstChild);
    
    setTimeout(() => {
        alertEl.style.animation = "coachFadeOut 0.4s forwards";
        setTimeout(() => {
            if (alertEl.parentNode) alertEl.remove();
        }, 400);
    }, 4500);
}

function processWord(word) {
    persistentConfig.totalWords++;

    if (isGibberish(word)) {
        persistentConfig.gibberishCount[word] = (persistentConfig.gibberishCount[word] || 0) + 1;
        showAlert(`⚠️ GIBBERISH: "${word}"`, "purple");
        saveStats();
        return;
    }

    if (STOPWORDS.includes(word)) return;

    const count = trackWord(word);

    if (count >= 2) {
        persistentConfig.wordCounts[word] = count;
        showCombo(word, count);
    } else {
        persistentConfig.wordCounts[word] = 1;
    }

    saveStats();
}

function processLivePreview(text) {
    const currentCounts = {};
    const words = text
        .toLowerCase()
        .split(/\s+/)
        .map(w => cleanWord(w));

    words.forEach(word => {
        if (!word) return;
        if (STOPWORDS.includes(word)) return;
        
        currentCounts[word] = (currentCounts[word] || 0) + 1;
        if (currentCounts[word] >= 2) {
            showCombo(word, currentCounts[word]);
        }
    });
}

function processFinalTranscript(text) {
    const words = text
        .toLowerCase()
        .split(/\s+/)
        .map(w => cleanWord(w));

    words.forEach(word => {
        if (!word) return;
        processWord(word);
    });
}

function startListening() {
    if (recognition) return;
    
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
        alert("Your browser does not support the Web Speech API natively. Please use Chrome/Edge.");
        return;
    }
    
    chrome.storage.local.get(['wordCounts', 'gibberishCount', 'totalWords'], (res) => {
        persistentConfig.wordCounts = res.wordCounts || {};
        persistentConfig.gibberishCount = res.gibberishCount || {};
        persistentConfig.totalWords = res.totalWords || 0;
    });
    
    recognition = new SpeechRecognition();
    recognition.continuous = true;
    recognition.interimResults = true;
    
    recognition.onstart = () => {
        console.log("🎙️ Speech Coach Active...");
        isListening = true;
        // wordHistory and previewCounts are NOT reset here to maintain continuity across chunks
    };

    recognition.onresult = function(event) {
        for (let i = event.resultIndex; i < event.results.length; i++) {
            const transcript = event.results[i][0].transcript;

            if (!event.results[i].isFinal) {
                processLivePreview(transcript);
            }

            if (event.results[i].isFinal) {
                processFinalTranscript(transcript);
                resetPreview();
            }
        }
    };
    
    recognition.onerror = (event) => {
        console.warn("Speech error:", event.error);
        if (event.error !== 'not-allowed') {
            if (isListening) {
                try { recognition.start(); } catch(e) {}
            }
        } else {
            alert("Microphone permission denied! Click the lock icon in the URL bar to allow microphone access, then refresh the page.");
            chrome.storage.local.set({ isListening: false });
            stopListening();
        }
    };

    recognition.onend = () => {
        chrome.storage.local.get(['isListening'], (res) => {
            if (res.isListening && isListening) {
                try { recognition.start(); } catch(e) {}
            }
        });
    };
    
    recognition.start();
}

function stopListening() {
    isListening = false;
    if (recognition) {
        recognition.stop();
        recognition = null;
        console.log("🛑 Speech Coach Stopped.");
    }
}

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === "START") {
        persistentConfig.wordCounts = {};
        persistentConfig.gibberishCount = {};
        persistentConfig.totalWords = 0;
        
        // Reset session-based tracking only on explicit start
        wordHistory = {}; 
        previewCounts = {};
        
        saveStats();
        
        startListening();
        sendResponse({status: "started"});
    } else if (request.action === "STOP") {
        stopListening();
        sendResponse({status: "stopped"});
    } else if (request.action === "STATUS") {
        sendResponse({isListening: isListening});
    }
});




