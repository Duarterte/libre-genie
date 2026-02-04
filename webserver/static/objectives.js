document.addEventListener('DOMContentLoaded', () => {
    // --- Auth Config ---
    const CLIENT_ID = localStorage.getItem("client_id");
    const SECRET = localStorage.getItem("client_secret");
    
    if (!CLIENT_ID || !SECRET) {
        console.warn("No credentials found. Chat page usually initializes them.");
    }

    const objectivesContainer = document.querySelector('.objectives-view');
    const addObjectiveBtn = document.querySelector('#add-obj-btn');
    
    // Modal Elements
    const modalOverlay = document.getElementById('genie-modal');
    const modalTitle = document.getElementById('modal-title');
    const modalInputTitle = document.getElementById('modal-input-title');
    const modalInputDesc = document.getElementById('modal-input-desc');
    const modalInputWeight = document.getElementById('modal-input-weight');
    const modalCancelBtn = document.getElementById('modal-cancel-btn');
    const modalConfirmBtn = document.getElementById('modal-confirm-btn');

    // State for modal
    let currentModalMode = 'objective'; // 'objective' or 'task'
    let currentObjectiveId = null;

    // Load initial data
    fetchObjectives();

    // --- Modal Logic ---
    function openModal(mode, objId = null) {
        currentModalMode = mode;
        currentObjectiveId = objId;

        // Reset fields
        modalInputTitle.value = '';
        modalInputDesc.value = '';
        modalInputWeight.value = '1';
        modalOverlay.classList.remove('hidden');

        if (mode === 'objective') {
            modalTitle.innerText = "New Objective";
            modalInputDesc.style.display = 'block'; 
            modalInputWeight.style.display = 'none';
        } else {
            modalTitle.innerText = "New Task";
            modalInputDesc.style.display = 'none';
            modalInputWeight.style.display = 'block';
        }
        modalInputTitle.focus();
    }

    function closeModal() {
        modalOverlay.classList.add('hidden');
    }

    modalCancelBtn.addEventListener('click', closeModal);
    modalOverlay.addEventListener('click', (e) => {
        if (e.target === modalOverlay) closeModal();
    });

    modalConfirmBtn.addEventListener('click', () => {
        const title = modalInputTitle.value.trim();
        const description = modalInputDesc.value.trim();
        const weight = parseInt(modalInputWeight.value) || 1;

        if (!title) {
            alert("Please enter a title.");
            return;
        }

        if (currentModalMode === 'objective') {
            createObjective(title, description);
        } else {
            createTask(currentObjectiveId, title, weight);
        }
        closeModal();
    });

    // --- Event Listeners ---
    addObjectiveBtn.addEventListener('click', () => {
        openModal('objective');
    });

    // --- API Functions ---

    async function fetchObjectives() {
        if (!CLIENT_ID) return;
        try {
            const res = await fetch(`/api/objectives?client_id=${CLIENT_ID}&secret=${SECRET}`);
            if (res.ok) {
                const data = await res.json();
                renderObjectives(data);
            }
        } catch (e) {
            console.error(e);
        }
    }

    async function createObjective(title, description) {
        try {
            const res = await fetch('/api/objectives', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    title, description, client_id: CLIENT_ID, secret: SECRET
                })
            });
            if (res.ok) fetchObjectives();
        } catch (e) { console.error(e); }
    }

    async function createTask(objectiveId, title, weight = 1) {
        try {
            const res = await fetch('/api/tasks', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    title, objective_id: objectiveId, weight, client_id: CLIENT_ID, secret: SECRET
                })
            });
            if (res.ok) fetchObjectives();
        } catch (e) { console.error(e); }
    }

    async function removeObjective(id) {
        if(!confirm("Delete this objective and all its tasks?")) return;
        try {
            const res = await fetch('/api/objectives', {
                method: 'DELETE',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ id, client_id: CLIENT_ID, secret: SECRET })
            });
            if (res.ok) fetchObjectives();
        } catch (e) { console.error(e); }
    }

    async function removeTask(id) {
        if(!confirm("Delete this task?")) return;
        try {
            const res = await fetch('/api/tasks', {
                method: 'DELETE',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ id, client_id: CLIENT_ID, secret: SECRET })
            });
            if (res.ok) fetchObjectives();
        } catch (e) { console.error(e); }
    }

    async function completeTask(id) {
        try {
            const res = await fetch('/api/tasks/complete', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ id, client_id: CLIENT_ID, secret: SECRET })
            });
            if (res.ok) fetchObjectives();
        } catch (e) { console.error(e); }
    }

    async function completeObjective(id) {
        if(!confirm("Complete this objective? This will add to your stats.")) return;
        try {
            const res = await fetch('/api/objectives/complete', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ id, client_id: CLIENT_ID, secret: SECRET })
            });
            if (res.ok) fetchObjectives();
        } catch (e) { console.error(e); }
    }

    function renderObjectives(objectives) {
        objectivesContainer.innerHTML = '';
        
        if (objectives.length === 0) {
            objectivesContainer.innerHTML = '<div style="text-align:center; color: gray;">No objectives yet.</div>';
            return;
        }

        objectives.forEach(obj => {
            const objDiv = document.createElement('div');
            objDiv.className = 'objective-item';
            
            // Status Tag Logic
            let statusTag = '';
            let statusClass = '';
            if (obj.status === 'completed') {
                statusTag = 'COMPLETED';
                statusClass = 'tag-completed';
            } else if (obj.status === 'in_progress') {
                statusTag = 'IN PROGRESS';
                statusClass = 'tag-progress';
            } else {
                statusTag = 'NOT STARTED';
                statusClass = 'tag-new';
            }

            // Header with delete button
            const header = document.createElement('div');
            header.className = 'objective-title';
            header.innerHTML = `
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <div style="display:flex; align-items:center; gap: 10px;">
                        <h3>${esc(obj.title)}</h3>
                        <span class="status-badge ${statusClass}">${statusTag}</span>
                    </div>
                    <span class="delete-icon" style="cursor:pointer; color:rgba(255,100,100,0.8);">&#10006;</span>
                </div>
            `;
            header.querySelector('.delete-icon').onclick = () => removeObjective(obj.id);

            const desc = document.createElement('div');
            desc.className = 'objective-description';
            desc.innerHTML = `<p>${esc(obj.description)}</p>`;

            const taskSection = document.createElement('div');
            taskSection.className = 'tasks-item';
            
            const ul = document.createElement('ul');
            let allTasksCompleted = obj.tasks.length > 0;

            obj.tasks.forEach(task => {
                const li = document.createElement('li');
                li.style.display = 'flex';
                li.style.justifyContent = 'space-between';
                li.style.alignItems = 'center';
                li.className = task.is_completed ? 'task-completed-item' : ''; // Use new class avoid conflict

                if (!task.is_completed) allTasksCompleted = false;

                li.innerHTML = `
                    <div style="display:flex; align-items:center;">
                        <span class="weight-badge" title="Weight: ${task.weight || 1}">${task.weight || 1}</span>
                        <span class="task-text">${esc(task.title)}</span>
                    </div>
                    <div style="display:flex; gap:10px; align-items:center;">
                        ${!task.is_completed ? `<button class="complete-task-btn" title="Complete Task"></button>` : `<span style="color:#00ff00;">✔</span>`}
                        <span class="delete-task-icon" title="Delete Task">&#10006;</span>
                    </div>
                `;
                li.querySelector('.delete-task-icon').onclick = () => removeTask(task.id);
                if (!task.is_completed) {
                    li.querySelector('.complete-task-btn').onclick = () => completeTask(task.id);
                }
                ul.appendChild(li);
            });

            const controlsDiv = document.createElement('div');
            controlsDiv.style.marginTop = '15px';
            controlsDiv.style.display = 'flex';
            controlsDiv.style.justifyContent = 'space-between';
            controlsDiv.style.alignItems = 'center';

            const addTaskBtn = document.createElement('button');
            addTaskBtn.className = 'add-task';
            addTaskBtn.innerText = 'Add Task';
            addTaskBtn.onclick = () => openModal('task', obj.id);

            // Complete Objective Button
            const completeObjBtn = document.createElement('button');
            completeObjBtn.className = 'complete-obj-btn';
            completeObjBtn.innerText = 'Complete Objective';
            if (!allTasksCompleted || obj.status === 'completed') {
                completeObjBtn.disabled = true;
                completeObjBtn.style.opacity = 0.5;
                completeObjBtn.style.cursor = 'not-allowed';
            }
            if (obj.status === 'completed') {
                completeObjBtn.innerText = 'Objective Completed';
            }
            
            completeObjBtn.onclick = () => completeObjective(obj.id);

            controlsDiv.appendChild(addTaskBtn);
            if (obj.tasks.length > 0) {
                 controlsDiv.appendChild(completeObjBtn);
            }

            taskSection.appendChild(ul);
            taskSection.appendChild(controlsDiv); // Append controls instead of just button

            objDiv.appendChild(header);
            objDiv.appendChild(desc);
            objDiv.appendChild(taskSection);
            
            objectivesContainer.appendChild(objDiv);
        });
    }

    function esc(str) {
        if(!str) return "";
        return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#039;");
    }
});
