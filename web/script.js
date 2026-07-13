let currentPool = [];       
let standbyBatches = [];
let dragSrcElement = null;  

const MONTH_ABBREVIATIONS = {
    "January": "Jan.", "February": "Feb.", "March": "Mar.", "April": "Apr.",
    "May": "May", "June": "Jun.", "July": "Jul.", "August": "Aug.",
    "September": "Sept.", "October": "Oct.", "November": "Nov.", "December": "Dec."
};

const daySelect = document.getElementById('daySelect');
for (let i = 1; i <= 31; i++) {
    let opt = document.createElement('option');
    opt.value = i; opt.innerText = i;
    daySelect.appendChild(opt);
}

document.getElementById('btnReroll').addEventListener('click', triggerPoolReroll);
document.getElementById('btnSave').addEventListener('click', saveToStandbyQueue);
document.getElementById('btnSaveConfig').addEventListener('click', commitPathsToConfiguration);

// Click listeners for the native file explorer hooks
document.getElementById('btnBrowseSource').addEventListener('click', () => selectDirectory('source'));
document.getElementById('btnBrowseVault').addEventListener('click', () => selectDirectory('vault'));

// Timeline change event listeners including our new year component
document.getElementById('yearSelect').addEventListener('change', () => triggerPoolReroll(false));
document.getElementById('monthSelect').addEventListener('change', () => triggerPoolReroll(false));
document.getElementById('daySelect').addEventListener('change', () => triggerPoolReroll(false));

document.getElementById('btnNextDate').addEventListener('click', () => shiftDateStep(1));
document.getElementById('btnPrevDate').addEventListener('click', () => shiftDateStep(-1));

function shiftDateStep(direction) {
    let day = parseInt(daySelect.value);
    let monthIdx = document.getElementById('monthSelect').selectedIndex;
    let yearSelect = document.getElementById('yearSelect');
    let year = parseInt(yearSelect.value);
    
    day += direction;
    
    if (day > 31) {
        day = 1;
        monthIdx += 1;
        if (monthIdx > 11) {
            monthIdx = 0;
            year += 1;
        }
    } else if (day < 1) {
        day = 31;
        monthIdx -= 1;
        if (monthIdx < 0) {
            monthIdx = 11;
            year -= 1;
        }
    }
    
    // Safety boundaries on year boundaries
    if (document.querySelector(`#yearSelect option[value="${year}"]`)) {
        yearSelect.value = year;
    }
    
    document.getElementById('monthSelect').selectedIndex = monthIdx;
    daySelect.value = day;
    triggerPoolReroll(false); 
}

// Calls Python to trigger the Tkinter native folder selection panel
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
        
        triggerPoolReroll(false);
        standbyBatches = [];
        await loadSavedBatchesFromDisk();
    }
}

async function triggerPoolReroll(isRerollAction = true) {
    const year = document.getElementById('yearSelect').value;
    const month = document.getElementById('monthSelect').value;
    const day = document.getElementById('daySelect').value;
    
    let lockedFiles = [];
    if (isRerollAction) {
        lockedFiles = currentPool.filter(item => item.locked).map(item => item.name);
    }
    
    const backendPayload = await eel.python_reroll_day_pool(year, month, day, lockedFiles)();
    
    currentPool = backendPayload.map(fileObject => {
        const wasLocked = lockedFiles.includes(fileObject.filename);
        return { name: fileObject.filename, locked: wasLocked };
    });
    
    renderGalleryDeckGrid();
}

function renderGalleryDeckGrid() {
    const container = document.getElementById('galleryContainer');
    container.innerHTML = '';
    
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
                <h6 class="mb-1 small fw-bold" style="color: #0095F6; font-family: monospace;">${batch.folderKey}</h6>
                <div class="text-white-50 small mb-1">Source: ${batch.dateDisplay}</div>
                <div class="small text-white-50 mb-3">${batch.count} files logged</div>
                <div class="d-flex gap-2">
                    <button class="btn btn-primary btn-sm fw-bold ig-btn-primary flex-grow-1" onclick="deployBatch('${batch.folderKey}')">Upload</button>
                    <button class="btn btn-outline-danger btn-sm fw-bold" style="padding: 0.25rem 0.5rem;" onclick="removeBatchFromPipeline('${batch.folderKey}')">Remove</button>
                </div>
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
    discovered.forEach(batch => {
        const parts = batch.dateDisplay.split(" "); // Format expected: "Month Day, Year"
        const month = parts[0];
        const day = parts[1].replace(",", "");
        const year = parts[2] || "2024";
        
        const computedCaption = generateAutoCaption(year, month, day);
        standbyBatches.push({
            folderKey: batch.folderKey,
            dateDisplay: batch.dateDisplay,
            count: batch.count,
            caption: computedCaption
        });
    });
    renderStandbyQueue();
}

async function init() {
    await loadPathsFromConfiguration();
    await triggerPoolReroll(false);
    await loadSavedBatchesFromDisk();
}
init();