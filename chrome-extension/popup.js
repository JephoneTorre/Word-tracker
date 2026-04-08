document.addEventListener('DOMContentLoaded', () => {
    const btn = document.getElementById('toggleBtn');
    const resetBtn = document.getElementById('clearBtn');
    const statusBadge = document.getElementById('statusBadge');
    
    // UI Elements
    const totalGibberishEl = document.getElementById('totalGibberish');
    const totalRepetitionsEl = document.getElementById('totalRepetitions');
    const topDisfluencyEl = document.getElementById('topDisfluency');
    const topWordsList = document.getElementById('topWordsList');

    function renderStats(wordCounts = {}, gibberishCount = {}, totalWords) {
        let totalGibberish = 0;
        let totalRepetitions = 0;
        let topDisfluencyName = "None";
        let maxDisfluencyCount = 0;
        
        let wordsArray = [];

        for (const [word, count] of Object.entries(gibberishCount)) {
            totalGibberish += count;
            wordsArray.push({ word, count, category: 'GIBBERISH' });
            if (count > maxDisfluencyCount) {
                maxDisfluencyCount = count;
                topDisfluencyName = word;
            }
        }

        for (const [word, count] of Object.entries(wordCounts)) {
            if (count >= 2) {
                totalRepetitions += count;
                wordsArray.push({ word, count, category: 'REPETITION' });
                if (count > maxDisfluencyCount) {
                    maxDisfluencyCount = count;
                    topDisfluencyName = word;
                }
            }
        }

        totalGibberishEl.textContent = totalGibberish;
        totalRepetitionsEl.textContent = totalRepetitions;
        topDisfluencyEl.textContent = topDisfluencyName.replace('_', ' ');

        // Top 6 Patterns
        wordsArray.sort((a, b) => b.count - a.count);
        const topWords = wordsArray.slice(0, 6);
        
        if (topWords.length > 0) {
            topWordsList.innerHTML = '';
            topWords.forEach(item => {
                const pill = document.createElement('div');
                pill.className = `word-pill cat-${item.category}`;
                pill.innerHTML = `${item.word.replace('_', ' ')} <span title="Total Occurrences">${item.count}x</span>`;
                topWordsList.appendChild(pill);
            });
        } else {
            topWordsList.innerHTML = '<div class="word-pill" style="opacity: 0.5; background: none;">No data yet.</div>';
        }
    }

    function syncUI() {
        chrome.storage.local.get(['isListening', 'wordCounts', 'gibberishCount', 'totalWords'], (res) => {
            if (res.isListening) {
                btn.textContent = "Stop Coaching";
                btn.classList.add("running");
                statusBadge.textContent = "Running";
                statusBadge.className = "status-badge running";
            } else {
                btn.textContent = "Start Coaching";
                btn.classList.remove("running");
                statusBadge.textContent = "Stopped";
                statusBadge.className = "status-badge stopped";
            }
            
            renderStats(res.wordCounts || {}, res.gibberishCount || {}, res.totalWords || 0);
        });
    }

    syncUI();

    // Listeners
    btn.addEventListener('click', () => {
        chrome.storage.local.get(['isListening'], (res) => {
            const isCurrentlyRunning = !!res.isListening;
            const newListeningState = !isCurrentlyRunning;
            
            chrome.storage.local.set({ isListening: newListeningState }, () => {
                syncUI();
                
                if (newListeningState) {
                    chrome.tabs.query({active: true, currentWindow: true}, function(tabs) {
                        if (tabs && tabs.length > 0) {
                            chrome.tabs.sendMessage(tabs[0].id, {action: "START"});
                        }
                    });
                } else {
                    chrome.tabs.query({}, function(tabs) {
                        for (let tab of tabs) {
                            chrome.tabs.sendMessage(tab.id, {action: "STOP"}).catch(() => {});
                        }
                    });
                }
            });
        });
    });

    resetBtn.addEventListener('click', () => {
        chrome.storage.local.set({ wordCounts: {}, gibberishCount: {}, totalWords: 0 }, () => {
            syncUI();
        });
    });
    
    // Automatically poll for dynamic changes when popup is open
    setInterval(syncUI, 2000);
});
