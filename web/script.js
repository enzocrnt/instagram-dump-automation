let currentPool = [];
let standbyBatches = [];

const MONTH_ABBREVIATIONS = {
    "January": "Jan.", "February": "Feb.", "March": "Mar.", "April": "Apr.",
    "May": "May", "June": "Jun.", "July": "Jul.", "August": "Aug.",
    "September": "Sept.", "October": "Oct.", "November": "Nov.", "December": "Dec."
};

const daySelect = document.getElementById('daySelect');
for (let i = 1; i <= 31; i++) {
    let opt = document.createElement('option');
    opt.value = i;
    opt.innerText = i;
    daySelect.appendChild(opt);
}

document.getElementById('btnReroll').addEventListener('click', triggerPoolReroll);
document.getElementById('btnSave').addEventListener('click', saveToStandbyQueue);
document.getElementById('monthSelect').addEventListener('change', triggerPoolReroll);
document.getElementById('daySelect').addEventListener('change', triggerPoolReroll);

async function triggerPoolReroll() {
    const month = document.getElementById('monthSelect').value;
    const day = document.getElementById('daySelect').value;
    
    currentPool = await eel.python_reroll_day_pool(month, day)();
    
    const container = document.getElementById('galleryContainer');
    container.innerHTML = '';
    
    currentPool.forEach((imgName) => {
        const wrapper = document.createElement('div');
        wrapper.className = 'thumb-block d-flex align-items-center justify-content-center overflow-hidden';
        wrapper.style.backgroundColor = '#121212';
        
        const img = document.createElement('img');
        img.src = `staging/${imgName}`;
        img.style.width = '100%';
        img.style.height = '100%';
        img.style.objectFit = 'cover';
        
        wrapper.appendChild(img);
        container.appendChild(wrapper);
    });
}

function generateAutoCaption(month, day) {
    const abbrev = MONTH_ABBREVIATIONS[month] || month;
    return `${abbrev} ${day}, 2024`;
}

// NEW: Scans your hard drive on boot and loads anything left un-uploaded
async function loadSavedBatchesFromDisk() {
    const discovered = await eel.python_load_existing_staged_batches()();
    
    discovered.forEach(batch => {
        // Break up recovered text to generate captions automatically
        const parts = batch.dateDisplay.split(" ");
        const month = parts[0];
        const day = parts[1];
        const computedCaption = generateAutoCaption(month, day);
        
        standbyBatches.push({
            folderKey: batch.folderKey,
            dateDisplay: batch.dateDisplay,
            count: batch.count,
            caption: computedCaption
        });
    });
    
    renderStandbyQueue();
}

async function saveToStandbyQueue() {
    if (currentPool.length === 0) return;

    const month = document.getElementById('monthSelect').value;
    const day = document.getElementById('daySelect').value;

    const activeFolderName = await eel.python_save_to_standby(month, day, currentPool)();
    const defaultCaption = generateAutoCaption(month, day);

    standbyBatches.push({
        folderKey: activeFolderName,
        dateDisplay: `${month} ${day}`,
        count: currentPool.length,
        caption: defaultCaption
    });

    renderStandbyQueue();
    autoAdvanceDate();
}

function renderStandbyQueue() {
    const container = document.getElementById('queueContainer');
    container.innerHTML = '';

    if (standbyBatches.length === 0) {
        container.innerHTML = `<p class="text-white-50 small font-italic p-3">No batches staged in standby. Curation Deck is ready.</p>`;
        return;
    }

    standbyBatches.forEach(batch => {
        const card = document.createElement('div');
        card.className = 'queue-card p-3 mb-3 d-flex align-items-start justify-content-between';
        
        card.innerHTML = `
            <div style="width: 45%;">
                <h6 class="mb-1 small fw-bold" style="color: #0095F6; text-transform: none; font-family: monospace;">${batch.folderKey}</h6>
                <div class="text-white-50 small mb-1">Source: ${batch.dateDisplay}</div>
                <div class="small text-white-50">${batch.count} files logged</div>
                <button class="btn btn-primary btn-sm mt-3 w-100 fw-bold ig-btn-primary" onclick="deployBatch('${batch.folderKey}')">🚀 Upload</button>
            </div>
            <div class="flex-grow-1 ms-3">
                <label class="text-white-50 small mb-1">Manual Caption Input:</label>
                <textarea class="form-control caption-area" rows="3" onkeyup="syncCaptionText('${batch.folderKey}', this.value)">${batch.caption}</textarea>
            </div>
        `;
        container.appendChild(card);
    });
}

function syncCaptionText(folderKey, value) {
    const batch = standbyBatches.find(b => b.folderKey === folderKey);
    if (batch) batch.caption = value;
}

async function deployBatch(folderKey) {
    const batchIndex = standbyBatches.findIndex(b => b.folderKey === folderKey);
    if (batchIndex === -1) return;
    
    const batch = standbyBatches[batchIndex];
    
    let success = await eel.python_upload_batch(batch.folderKey, batch.caption)();
    if (success) {
        standbyBatches.splice(batchIndex, 1);
        renderStandbyQueue();
    }
}

function autoAdvanceDate() {
    let day = parseInt(daySelect.value);
    if (day < 31) {
        daySelect.value = day + 1;
    } else {
        daySelect.value = 1;
        let monthIdx = document.getElementById('monthSelect').selectedIndex;
        document.getElementById('monthSelect').selectedIndex = (monthIdx + 1) % 12;
    }
    triggerPoolReroll();
}

// Boot Initialization Setup
async function init() {
    await triggerPoolReroll();
    await loadSavedBatchesFromDisk(); // Triggers scan check on launch
}

init();