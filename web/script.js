let currentPool = [];       
let standbyBatches = [];
let dragSrcElement = null;  

const MONTH_DAYS_MAP = {
    "January": 31, "February": 28, "March": 31, "April": 30, "May": 31, "June": 30,
    "July": 31, "August": 31, "September": 30, "October": 31, "November": 30, "December": 31
};

const MONTH_ABBREVIATIONS = {
    "January": "Jan.", "February": "Feb.", "March": "Mar.", "April": "Apr.",
    "May": "May", "June": "Jun.", "July": "Jul.", "August": "Aug.",
    "September": "Sept.", "October": "Oct.", "November": "Nov.", "December": "Dec."
};

// Global Interactive DOM Event Listeners
document.getElementById('btnReroll').addEventListener('click', triggerPoolReroll);
document.getElementById('btnSave').addEventListener('click', saveToStandbyQueue);
document.getElementById('btnSaveConfig').addEventListener('click', commitPathsToConfiguration);
document.getElementById('btnBrowseSource').addEventListener('click', () => selectDirectory('source'));
document.getElementById('btnBrowseVault').addEventListener('click', () => selectDirectory('vault'));

document.getElementById('yearSelect').addEventListener('change', () => { updateAdaptiveDayLimits(); triggerPoolReroll(false); });
document.getElementById('monthSelect').addEventListener('change', () => { updateAdaptiveDayLimits(); triggerPoolReroll(false); });
document.getElementById('daySelect').addEventListener('change', () => triggerPoolReroll(false));

document.getElementById('btnNextDate').addEventListener('click', () => shiftDateStep(1));
document.getElementById('btnPrevDate').addEventListener('click', () => shiftDateStep(-1));

// Adaptive Calendar Bounds Engine
function updateAdaptiveDayLimits() {
    const year = parseInt(document.getElementById('yearSelect').value);
    const month = document.getElementById('monthSelect').value;
    const daySelect = document.getElementById('daySelect');
    
    let maxDays = MONTH_DAYS_MAP[month] || 31;
    
    if (month === "February") {
        const isLeap = (year % 4 === 0 && year % 100 !== 0) || (year % 400 === 0);
        maxDays = isLeap ? 29 : 28;
    }
    
    const currentVal = parseInt(daySelect.value) || 1;
    daySelect.innerHTML = '';
    
    for (let i = 1; i <= maxDays; i++) {
        let opt = document.createElement('option');
        opt.value = i; opt.innerText = i;
        daySelect.appendChild(opt);
    }
    
    daySelect.value = Math.min(currentVal, maxDays);
}

function shiftDateStep(direction) {
    const daySelect = document.getElementById('daySelect');
    let day = parseInt(daySelect.value);
    let monthIdx = document.getElementById('monthSelect').selectedIndex;
    let yearSelect = document.getElementById('yearSelect');
    let year = parseInt(yearSelect.value);
    
    const maxDaysInMonth = daySelect.options.length;
    day += direction;
    
    if (day > maxDaysInMonth) {
        day = 1;
        monthIdx += 1;
        if (monthIdx > 11) {
            monthIdx = 0;
            year += 1;
        }
    } else if (day < 1) {
        monthIdx -= 1;
        if (monthIdx < 0) {
            monthIdx = 11;
            year -= 1;
        }
        document.getElementById('monthSelect').selectedIndex = monthIdx;
        updateAdaptiveDayLimits();
        day = daySelect.options.length; 
    }
    
    if (document.querySelector(`#yearSelect option[value="${year}"]`)) {
        yearSelect.value = year;
    }
    
    document.getElementById('monthSelect').selectedIndex = monthIdx;
    updateAdaptiveDayLimits();
    daySelect.value = day;
    triggerPoolReroll(false); 
}

async function selectDirectory(targetField) {
    const defaultPath = targetField === 'source' 
        ? document.getElementById('cfgSourcePath').value 
        : document.getElementById('cfgVaultPath').value;

    const chosenPath = await eel.python_open_folder_picker(defaultPath)();
    
    if (chosenPath) {
        if (targetField === 'source') {
            document.getElementById('cfgSourcePath').value = chosenPath;
        } else {
            document.getElementById('cfgVaultPath').value = chosenPath;
        }
    }
}

async function loadPathsFromConfiguration() {
    const config = await eel.python_get_paths_config()();
    document.getElementById('cfgSourcePath').value = config.source_dir || "";
    document.getElementById('cfgVaultPath').value = config.vault_dir || "";
}

async function commitPathsToConfiguration() {
    const sourcePath = document.getElementById('cfgSourcePath').value;
    const vaultPath = document.getElementById('cfgVaultPath').value;
    
    const success = await eel.python_save_paths_config(sourcePath, vaultPath)();
    if (success) {
        const saveBtn = document.getElementById('btnSaveConfig');
        saveBtn.innerText = "Saved!";
        saveBtn.className = "btn btn-success btn-sm w-100 h-100 fw-bold py-1";
        setTimeout(() => {
            saveBtn.innerText = "Save Paths";
            saveBtn.className = "btn btn-outline-primary btn-sm w-100 fw-bold py-1";
        }, 2000);
        
        await verifyActiveDriveStatus();
        standbyBatches = [];
        await loadSavedBatchesFromDisk();
    }
}

async function verifyActiveDriveStatus() {
    const connected = await eel.python_verify_source_connection()();
    const banner = document.getElementById('driveWarningBanner');
    if (!connected) {
        banner.classList.remove('d-none');
        return false;
    } else {
        banner.classList.add('d-none');
        return true;
    }
}

async function triggerPoolReroll(isRerollAction = true) {
    const driveReady = await verifyActiveDriveStatus();
    if (!driveReady) {
        currentPool = [];
        renderGalleryDeckGrid();
        return;
    }

    const year = document.getElementById('yearSelect').value;
    const month = document.getElementById('monthSelect').value;
    const day = document.getElementById('daySelect').value;
    
    let lockedFiles = [];
    if (isRerollAction) {
        lockedFiles = currentPool.filter(item => item.locked).map(item => item.name);
    }
    
    const overlay = document.getElementById('deckLoadingOverlay');
    overlay.classList.remove('d-none');

    const backendPayload = await eel.python_reroll_day_pool(year, month, day, lockedFiles)();
    
    currentPool = backendPayload.map(fileObject => {
        const wasLocked = lockedFiles.includes(fileObject.filename);
        return { name: fileObject.filename, locked: wasLocked };
    });
    
    renderGalleryDeckGrid();
    overlay.classList.add('d-none');
}

function renderGalleryDeckGrid() {
    const container = document.getElementById('galleryContainer');
    container.innerHTML = '';
    
    if (currentPool.length === 0) {
        container.innerHTML = `<p class="text-white-50 small font-italic p-3 m-0">No photos found matching this date query.</p>`;
        return;
    }

    currentPool.forEach((item, index) => {
        const wrapper = document.createElement('div');
        wrapper.className = `thumb-block overflow-hidden ${item.locked ? 'locked' : ''}`;
        wrapper.setAttribute('draggable', 'true');
        wrapper.setAttribute('data-index', index);
        
        wrapper.addEventListener('dragstart', handleDragStart);
        wrapper.addEventListener('dragover', handleDragOver);
        wrapper.addEventListener('drop', handleDrop);
        wrapper.addEventListener('dragend', handleDragEnd);
        
        wrapper.addEventListener('click', (e) => {
            if (e.target.tagName === 'IMG' || e.target === wrapper) {
                item.locked = !item.locked;
                renderGalleryDeckGrid();
            }
        });
        
        const img = document.createElement('img');
        img.src = `staging/${item.name}`;
        img.style.width = '100%'; img.style.height = '100%'; img.style.objectFit = 'cover';
        
        wrapper.appendChild(img);
        
        if (item.locked) {
            const badge = document.createElement('div');
            badge.className = 'lock-badge';
            badge.innerText = 'LOCKED';
            wrapper.appendChild(badge);
        }
        
        container.appendChild(wrapper);
    });
}

function handleDragStart(e) {
    this.classList.add('dragging');
    dragSrcElement = this;
    e.dataTransfer.effectAllowed = 'move';
}
function handleDragOver(e) {
    if (e.preventDefault) e.preventDefault();
    return false;
}
function handleDrop(e) {
    if (e.stopPropagation) e.stopPropagation();
    
    if (dragSrcElement !== this) {
        const fromIdx = parseInt(dragSrcElement.getAttribute('data-index'));
        const toIdx = parseInt(this.getAttribute('data-index'));
        
        const targetElement = currentPool.splice(fromIdx, 1)[0];
        currentPool.splice(toIdx, 0, targetElement);
        
        renderGalleryDeckGrid();
    }
    return false;
}
function handleDragEnd() {
    this.classList.remove('dragging');
}

function generateAutoCaption(year, month, day) {
    return `${MONTH_ABBREVIATIONS[month] || month} ${day}, ${year}`;
}

async function saveToStandbyQueue() {
    if (currentPool.length === 0) return;

    const year = document.getElementById('yearSelect').value;
    const month = document.getElementById('monthSelect').value;
    const day = document.getElementById('daySelect').value;
    
    const orderedFilenames = currentPool.map(item => item.name);

    const activeFolderName = await eel.python_save_to_standby(year, month, day, orderedFilenames)();
    const defaultCaption = generateAutoCaption(year, month, day);

    standbyBatches.push({
        folderKey: activeFolderName,
        dateDisplay: `${month} ${day}, ${year}`,
        count: orderedFilenames.length,
        caption: defaultCaption
    });

    renderStandbyQueue();
    shiftDateStep(1); 
}

// Fully Responsive Mobile-Adaptive Component Renderer
function renderStandbyQueue() {
    const container = document.getElementById('queueContainer');
    container.innerHTML = '';

    if (standbyBatches.length === 0) {
        container.innerHTML = `<p class="text-white-50 small font-italic p-3">No batches staged in standby. Curation Deck is ready.</p>`;
        return;
    }

    standbyBatches.forEach(batch => {
        const card = document.createElement('div');
        card.className = 'queue-card p-3 mb-3 d-flex flex-wrap flex-sm-nowrap align-items-start justify-content-between gap-3';
        card.innerHTML = `
            <div class="flex-grow-1 min-w-0" style="flex-basis: 200px;">
                <h6 class="mb-1 small fw-bold text-truncate" style="color: #0095F6; font-family: monospace;" title="${batch.folderKey}">${batch.folderKey}</h6>
                <div class="text-white-50 small mb-1">Source: ${batch.dateDisplay}</div>
                <div class="small text-white-50 mb-3">${batch.count} files logged</div>
                
                <div class="d-flex flex-wrap gap-2 align-items-center w-100">
                    <button class="btn btn-primary btn-sm fw-bold ig-btn-primary flex-grow-1 py-1" style="min-width: 70px; height: 31px;" onclick="deployBatch('${batch.folderKey}')">Upload</button>
                    <button class="btn btn-outline-secondary btn-sm py-1 px-2 d-flex align-items-center justify-content-center" style="height: 31px; min-width: 36px;" onclick="openBatchInExplorer('${batch.folderKey}')">📂</button>
                    <button class="btn btn-outline-danger btn-sm fw-bold py-1 flex-grow-1" style="min-width: 75px; height: 31px;" onclick="removeBatchFromPipeline('${batch.folderKey}')">Remove</button>
                </div>
            </div>
            
            <div class="flex-grow-1 w-100" style="flex-basis: 220px;">
                <label class="text-white-50 small mb-1">Manual Caption Input:</label>
                <textarea class="form-control caption-area w-100" rows="3" style="resize: none;" onkeyup="syncCaptionText('${batch.folderKey}', this.value)">${batch.caption}</textarea>
            </div>
        `;
        container.appendChild(card);
    });
}

async function syncCaptionText(folderKey, value) {
    const batch = standbyBatches.find(b => b.folderKey === folderKey);
    if (batch) {
        batch.caption = value;
        // Push modification back to system storage file asynchronously
        await eel.python_sync_caption_file(folderKey, value)();
    }
}

async function openBatchInExplorer(folderKey) {
    await eel.python_open_batch_in_explorer(folderKey)();
}

async function removeBatchFromPipeline(folderKey) {
    const confirmed = await eel.python_delete_batch_folder(folderKey)();
    if (confirmed) {
        const batchIndex = standbyBatches.findIndex(b => b.folderKey === folderKey);
        if (batchIndex !== -1) {
            standbyBatches.splice(batchIndex, 1);
            renderStandbyQueue();
        }
    }
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

async function loadSavedBatchesFromDisk() {
    const discovered = await eel.python_load_existing_staged_batches()();
    standbyBatches = []; 
    discovered.forEach(batch => {
        standbyBatches.push({
            folderKey: batch.folderKey,
            dateDisplay: batch.dateDisplay,
            count: batch.count,
            caption: batch.caption
        });
    });
    renderStandbyQueue();
}

async function init() {
    updateAdaptiveDayLimits();
    await loadPathsFromConfiguration();
    const activeDrive = await verifyActiveDriveStatus();
    if (activeDrive) {
        await triggerPoolReroll(false);
    }
    await loadSavedBatchesFromDisk();
}
init();