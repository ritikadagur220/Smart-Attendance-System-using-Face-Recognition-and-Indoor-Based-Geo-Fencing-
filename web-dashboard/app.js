

let db = null;
let isFirebaseMode = false;

let demoStudents = [];
let demoBeacons = [];
let demoAttendance = [];

document.addEventListener('DOMContentLoaded', () => {
    checkAuth();
    initApp();
});

function checkAuth() {
    if (typeof firebase !== 'undefined' && firebase.apps.length > 0 && firebase.auth) {
        firebase.auth().onAuthStateChanged(user => {
            if (user) {
                document.getElementById('userEmail').textContent = user.email || 'Teacher';
            } else {
                window.location.href = 'login.html';
            }
        });
    } else {

        const demoUser = sessionStorage.getItem('demoUser');
        if (demoUser) {
            const user = JSON.parse(demoUser);
            document.getElementById('userEmail').textContent = user.email || 'Teacher (Demo)';
        } else {
            document.getElementById('userEmail').textContent = 'Teacher (Demo)';
        }
    }
}

function initApp() {

    if (typeof firebase !== 'undefined' && firebase.apps.length > 0) {
        try {
            db = firebase.firestore();
            isFirebaseMode = true;
            console.log("✅ Firestore connected — LIVE mode");
            startRealtimeListeners();
        } catch (e) {
            console.warn("⚠️ Firestore not available:", e.message);
            isFirebaseMode = false;
            loadDemoData();
        }
    } else {
        console.log("⚡ Running in local mode");
        isFirebaseMode = false;
        loadDemoData();
    }
}

function switchTab(tabName) {

    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.tab === tabName);
    });

    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.toggle('active', content.id === `tab-${tabName}`);
    });
}

function startRealtimeListeners() {
    if (!db) return;
    
    const today = new Date().toISOString().split('T')[0];

    db.collection('attendance')
        .where('date', '==', today)
        .onSnapshot(snapshot => {
            const records = [];
            snapshot.forEach(doc => records.push({ id: doc.id, ...doc.data() }));
            renderAttendance(records);
        }, err => console.error("Attendance listener error:", err));

    db.collection('students')
        .onSnapshot(snapshot => {
            const students = [];
            snapshot.forEach(doc => students.push({ id: doc.id, ...doc.data() }));
            renderStudents(students);
            document.getElementById('statTotal').textContent = students.length;
        }, err => console.error("Students listener error:", err));

    db.collection('beacons')
        .onSnapshot(snapshot => {
            const beacons = [];
            snapshot.forEach(doc => beacons.push({ id: doc.id, ...doc.data() }));
            renderBeacons(beacons);
            document.getElementById('statBeacons').textContent = beacons.filter(b => b.active).length;
        }, err => console.error("Beacons listener error:", err));
}

function loadDemoData() {
    renderStudents(demoStudents);
    renderBeacons(demoBeacons);
    renderAttendance(demoAttendance);
    updateStats();
}

function startDemoSimulation() {
}

function renderAttendance(records) {
    const tbody = document.getElementById('attendanceBody');
    const empty = document.getElementById('attendanceEmpty');
    
    if (records.length === 0) {
        tbody.innerHTML = '';
        empty.style.display = 'block';
        return;
    }
    
    empty.style.display = 'none';

    const sorted = [...records].sort((a, b) => {
        const timeA = a.entry_time ? new Date(a.entry_time).getTime() : 0;
        const timeB = b.entry_time ? new Date(b.entry_time).getTime() : 0;
        return timeB - timeA;
    });
    
    tbody.innerHTML = sorted.map(record => {
        const entryTime = record.entry_time ? formatTime(record.entry_time) : '—';
        const exitTime = record.exit_time ? formatTime(record.exit_time) : '—';
        const statusClass = record.status === 'PRESENT' ? 'present' : 'exit';
        const dotClass = record.status === 'PRESENT' ? 'green' : 'red';
        
        return `
            <tr>
                <td><strong>${escapeHtml(record.student_name || 'Unknown')}</strong></td>
                <td>
                    <span class="badge ${statusClass}">
                        <span class="pulse-dot ${dotClass}"></span>
                        ${record.status}
                    </span>
                </td>
                <td>${entryTime}</td>
                <td>${exitTime}</td>
                <td>${escapeHtml(record.classroom || '—')}</td>
                <td>${record.rssi || '—'}</td>
            </tr>
        `;
    }).join('');
}

function renderStudents(students) {
    const tbody = document.getElementById('studentsBody');
    const empty = document.getElementById('studentsEmpty');
    
    if (students.length === 0) {
        tbody.innerHTML = '';
        empty.style.display = 'block';
        return;
    }
    
    empty.style.display = 'none';
    
    tbody.innerHTML = students.map(student => {
        const regDate = student.registered_at ? formatDate(student.registered_at) : '—';
        return `
            <tr>
                <td><strong>${escapeHtml(student.name)}</strong></td>
                <td>${escapeHtml(student.email)}</td>
                <td><code style="color:var(--accent-blue);font-size:12px">${escapeHtml(student.device_id)}</code></td>
                <td>${regDate}</td>
                <td>
                    <button class="btn-action delete" onclick="deleteStudent('${student.id}')">Delete</button>
                </td>
            </tr>
        `;
    }).join('');
}

function renderBeacons(beacons) {
    const tbody = document.getElementById('beaconsBody');
    const empty = document.getElementById('beaconsEmpty');
    
    if (beacons.length === 0) {
        tbody.innerHTML = '';
        empty.style.display = 'block';
        return;
    }
    
    empty.style.display = 'none';
    
    tbody.innerHTML = beacons.map(beacon => {
        const statusClass = beacon.active ? 'active-badge' : 'exit';
        const statusText = beacon.active ? 'Active' : 'Inactive';
        return `
            <tr>
                <td><code style="font-size:13px">${escapeHtml(beacon.device_name)}</code></td>
                <td>${escapeHtml(beacon.classroom)}</td>
                <td>${beacon.rssi_threshold_present || -75} dBm</td>
                <td>${beacon.rssi_threshold_exit || -85} dBm</td>
                <td><span class="badge ${statusClass}">${statusText}</span></td>
                <td>
                    <button class="btn-action delete" onclick="deleteBeacon('${beacon.id}')">Delete</button>
                </td>
            </tr>
        `;
    }).join('');
}

async function addStudent() {
    const name = document.getElementById('studentName').value.trim();
    const email = document.getElementById('studentEmail').value.trim();
    const deviceId = document.getElementById('studentDeviceId').value.trim();
    
    if (!name || !email || !deviceId) {
        showToast("Please fill in all fields", "error");
        return;
    }
    
    const studentId = 'STU' + Date.now().toString().slice(-6);
    const data = {
        id: studentId,
        name: name,
        email: email,
        device_id: deviceId,
        registered_at: new Date().toISOString(),
    };
    
    if (isFirebaseMode && db) {
        try {
            await db.collection('students').doc(studentId).set(data);
            showToast(`Student "${name}" added successfully`, "success");
        } catch (err) {
            showToast("Failed to add student: " + err.message, "error");
        }
    } else {
        demoStudents.push(data);
        renderStudents(demoStudents);
        updateStats();
        showToast(`Student "${name}" added (Demo)`, "success");
    }

    document.getElementById('studentName').value = '';
    document.getElementById('studentEmail').value = '';
    document.getElementById('studentDeviceId').value = '';
}

async function deleteStudent(studentId) {
    if (!confirm("Are you sure you want to delete this student?")) return;
    
    if (isFirebaseMode && db) {
        try {
            await db.collection('students').doc(studentId).delete();
            showToast("Student deleted", "info");
        } catch (err) {
            showToast("Failed to delete: " + err.message, "error");
        }
    } else {
        demoStudents = demoStudents.filter(s => s.id !== studentId);
        renderStudents(demoStudents);
        updateStats();
        showToast("Student deleted (Demo)", "info");
    }
}

async function addBeacon() {
    const deviceName = document.getElementById('beaconName').value.trim();
    const classroom = document.getElementById('beaconClassroom').value.trim();
    
    if (!classroom) {
        showToast("Please enter a classroom name", "error");
        return;
    }
    
    const beaconId = 'BCN' + Date.now().toString().slice(-6);
    const data = {
        id: beaconId,
        device_name: deviceName,
        classroom: classroom,
        rssi_threshold_present: -75,
        rssi_threshold_exit: -85,
        active: true,
    };
    
    if (isFirebaseMode && db) {
        try {
            await db.collection('beacons').doc(beaconId).set(data);
            showToast(`Beacon for "${classroom}" added`, "success");
        } catch (err) {
            showToast("Failed to add beacon: " + err.message, "error");
        }
    } else {
        demoBeacons.push(data);
        renderBeacons(demoBeacons);
        updateStats();
        showToast(`Beacon for "${classroom}" added (Demo)`, "success");
    }
    
    document.getElementById('beaconClassroom').value = '';
}

async function deleteBeacon(beaconId) {
    if (!confirm("Are you sure you want to delete this beacon?")) return;
    
    if (isFirebaseMode && db) {
        try {
            await db.collection('beacons').doc(beaconId).delete();
            showToast("Beacon deleted", "info");
        } catch (err) {
            showToast("Failed to delete: " + err.message, "error");
        }
    } else {
        demoBeacons = demoBeacons.filter(b => b.id !== beaconId);
        renderBeacons(demoBeacons);
        updateStats();
        showToast("Beacon deleted (Demo)", "info");
    }
}

function updateStats() {
    document.getElementById('statTotal').textContent = demoStudents.length;
    document.getElementById('statPresent').textContent = demoAttendance.filter(a => a.status === 'PRESENT').length;
    document.getElementById('statExited').textContent = demoAttendance.filter(a => a.status === 'EXIT').length;
    document.getElementById('statBeacons').textContent = demoBeacons.filter(b => b.active).length;
}

function formatTime(isoString) {
    try {
        const d = new Date(isoString);
        return d.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    } catch {
        return '—';
    }
}

function formatDate(isoString) {
    try {
        const d = new Date(isoString);
        return d.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' });
    } catch {
        return '—';
    }
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function showToast(message, type = 'info') {
    const container = document.getElementById('toastContainer');
    const icons = { success: '✅', error: '❌', info: 'ℹ️' };
    
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `<span>${icons[type] || 'ℹ️'}</span> ${escapeHtml(message)}`;
    
    container.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(100px)';
        toast.style.transition = 'all 0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

function handleLogout() {
    closeFacePanel();
    if (typeof firebase !== 'undefined' && firebase.apps.length > 0 && firebase.auth) {
        firebase.auth().signOut().then(() => {
            sessionStorage.removeItem('demoUser');
            window.location.href = 'login.html';
        });
    } else {
        sessionStorage.removeItem('demoUser');
        window.location.href = 'login.html';
    }
}

const FACE_API_BASE = 'http://localhost:8080/api';
let faceStream = null;
let faceMode = 'verify';
let registerCaptureCount = 0;
let faceAttendanceRecords = [];

function startFaceVerify() {
    faceMode = 'verify';
    document.getElementById('facePanelTitle').textContent = '\ud83d\udcf8 Face Verification - Take Attendance';
    document.getElementById('faceRegForm').style.display = 'none';
    document.getElementById('faceCaptureBtn').textContent = '\ud83d\udcf8 Capture & Verify';
    document.getElementById('faceResult').innerHTML = '<p style="color:var(--text-muted); text-align:center">Point your camera at a face and click Capture</p>';
    openFacePanel();
}

function startFaceRegister() {
    faceMode = 'register';
    registerCaptureCount = 0;
    document.getElementById('facePanelTitle').textContent = '\ud83c\udd94 Register Student Face';
    document.getElementById('faceRegForm').style.display = 'block';
    document.getElementById('faceCaptureBtn').textContent = '\ud83d\udcf8 Capture Face (0/5)';
    document.getElementById('faceResult').innerHTML = '<p style="color:var(--text-muted); text-align:center">Enter student info, then capture 5 face images from different angles</p>';
    openFacePanel();
}

async function openFacePanel() {
    const panel = document.getElementById('facePanel');
    panel.style.display = 'block';
    
    try {
        faceStream = await navigator.mediaDevices.getUserMedia({ 
            video: { width: 640, height: 480, facingMode: 'user' } 
        });
        const video = document.getElementById('faceVideo');
        video.srcObject = faceStream;
        showToast("Camera started", "success");
    } catch (err) {
        showToast("Cannot access camera: " + err.message, "error");
        document.getElementById('faceResult').innerHTML = 
            `<p style="color:var(--accent-red); text-align:center">Camera access denied.<br>Please allow camera permissions.</p>`;
    }

    checkFaceApiStatus();
}

function closeFacePanel() {
    const panel = document.getElementById('facePanel');
    if (panel) panel.style.display = 'none';
    
    if (faceStream) {
        faceStream.getTracks().forEach(track => track.stop());
        faceStream = null;
    }
    const video = document.getElementById('faceVideo');
    if (video) video.srcObject = null;
}

async function captureAndProcess() {
    const video = document.getElementById('faceVideo');
    const canvas = document.getElementById('faceCanvas');
    
    if (!video.srcObject) {
        showToast("Camera not active", "error");
        return;
    }

    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext('2d');
    ctx.drawImage(video, 0, 0);

    const imageBase64 = canvas.toDataURL('image/jpeg', 0.8);
    
    if (faceMode === 'verify') {
        await verifyFace(imageBase64);
    } else {
        await registerFace(imageBase64);
    }
}

async function verifyFace(imageBase64) {
    const resultDiv = document.getElementById('faceResult');
    resultDiv.innerHTML = '<p style="color:var(--accent-blue); text-align:center">Verifying face...</p>';
    
    try {
        const response = await fetch(`${FACE_API_BASE}/face/verify`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ image: imageBase64 }),
        });
        
        const result = await response.json();
        
        if (result.verified) {
            const confColor = result.confidence > 70 ? 'var(--accent-green)' : 'var(--accent-amber)';
            resultDiv.innerHTML = `
                <div style="text-align:center">
                    <div style="font-size:48px; margin-bottom:12px">\u2705</div>
                    <h3 style="color:var(--accent-green); margin-bottom:8px">VERIFIED</h3>
                    <p style="font-size:20px; font-weight:700; margin-bottom:4px">${escapeHtml(result.student_name)}</p>
                    <p style="color:var(--text-secondary); margin-bottom:12px">ID: ${escapeHtml(result.student_id)}</p>
                    <div style="display:inline-block; padding:8px 20px; border-radius:20px; background:${confColor}20; border:1px solid ${confColor}40; color:${confColor}; font-weight:600">
                        Confidence: ${result.confidence}%
                    </div>
                    <p style="color:var(--text-muted); margin-top:16px; font-size:13px">
                        ${result.attendance === 'ALREADY_PRESENT' ? 'Already marked present today' : 'Attendance marked successfully!'}
                    </p>
                </div>
            `;
            
            if (result.attendance === 'MARKED_PRESENT') {
                addFaceAttendanceRecord(result.student_id, result.student_name, result.confidence);
                showToast(`${result.student_name} marked PRESENT via face`, "success");
            } else {
                showToast(result.message, "info");
            }
        } else {
            resultDiv.innerHTML = `
                <div style="text-align:center">
                    <div style="font-size:48px; margin-bottom:12px">\u274c</div>
                    <h3 style="color:var(--accent-red); margin-bottom:8px">NOT VERIFIED</h3>
                    <p style="color:var(--text-secondary)">${escapeHtml(result.message)}</p>
                </div>
            `;
            showToast(result.message, "error");
        }
    } catch (err) {
        resultDiv.innerHTML = `
            <div style="text-align:center">
                <div style="font-size:48px; margin-bottom:12px">\u26a0\ufe0f</div>
                <h3 style="color:var(--accent-amber); margin-bottom:8px">API Not Available</h3>
                <p style="color:var(--text-secondary)">Face recognition server is not running.</p>
                <p style="color:var(--text-muted); font-size:13px; margin-top:12px">
                    Start it with: <code style="color:var(--accent-blue)">python python-backend/face_api_server.py</code>
                </p>
            </div>
        `;
    }
}

async function registerFace(imageBase64) {
    const studentId = document.getElementById('faceStudentId').value.trim();
    const studentName = document.getElementById('faceStudentName').value.trim();
    const resultDiv = document.getElementById('faceResult');
    
    if (!studentId || !studentName) {
        showToast("Please enter Student ID and Name", "error");
        return;
    }
    
    resultDiv.innerHTML = '<p style="color:var(--accent-blue); text-align:center">Registering face...</p>';
    
    try {
        const response = await fetch(`${FACE_API_BASE}/face/register`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                student_id: studentId,
                student_name: studentName,
                image: imageBase64,
                index: registerCaptureCount,
            }),
        });
        
        const result = await response.json();
        
        if (result.success) {
            registerCaptureCount++;
            document.getElementById('faceCaptureBtn').textContent = `\ud83d\udcf8 Capture Face (${registerCaptureCount}/5)`;
            
            resultDiv.innerHTML = `
                <div style="text-align:center">
                    <div style="font-size:48px; margin-bottom:12px">\u2705</div>
                    <h3 style="color:var(--accent-green); margin-bottom:8px">Image ${registerCaptureCount}/5 Captured</h3>
                    <p style="color:var(--text-secondary)">${escapeHtml(result.message)}</p>
                    <p style="color:var(--text-muted); margin-top:12px; font-size:13px">
                        ${registerCaptureCount >= 5 ? 'All images captured! Click Train to build the model.' : 'Look at a slightly different angle and capture again.'}
                    </p>
                </div>
            `;
            showToast(result.message, "success");
        } else {
            resultDiv.innerHTML = `
                <div style="text-align:center">
                    <div style="font-size:48px; margin-bottom:12px">\u274c</div>
                    <p style="color:var(--accent-red)">${escapeHtml(result.message)}</p>
                </div>
            `;
            showToast(result.message, "error");
        }
    } catch (err) {
        resultDiv.innerHTML = `
            <div style="text-align:center">
                <h3 style="color:var(--accent-amber)">API Not Available</h3>
                <p style="color:var(--text-muted); font-size:13px; margin-top:8px">
                    Start: <code style="color:var(--accent-blue)">python python-backend/face_api_server.py</code>
                </p>
            </div>
        `;
    }
}

async function trainFaceModel() {
    showToast("Training model...", "info");
    
    try {
        const response = await fetch(`${FACE_API_BASE}/face/train`, {
            method: 'POST',
        });
        const result = await response.json();
        
        if (result.success) {
            showToast(`Model trained: ${result.images} images from ${result.students} students`, "success");
        } else {
            showToast(result.message || "Training failed", "error");
        }
    } catch (err) {
        showToast("Face API server not running. Start: python python-backend/face_api_server.py", "error");
    }

    checkFaceApiStatus();
}

async function checkFaceApiStatus() {
    try {
        const response = await fetch(`${FACE_API_BASE}/face/status`);
        const status = await response.json();
        
        const el = document.getElementById('faceStatusCount');
        if (el) el.textContent = status.registered_students || 0;
    } catch {
        const el = document.getElementById('faceStatusCount');
        if (el) el.textContent = '--';
    }
}

function addFaceAttendanceRecord(studentId, studentName, confidence) {
    faceAttendanceRecords.unshift({
        student_id: studentId,
        student_name: studentName,
        time: new Date().toISOString(),
        confidence: confidence,
        status: 'PRESENT',
        method: 'FACE',
    });
    renderFaceAttendance();
}

function renderFaceAttendance() {
    const tbody = document.getElementById('faceAttendanceBody');
    const empty = document.getElementById('faceAttendanceEmpty');
    
    if (!tbody) return;
    
    if (faceAttendanceRecords.length === 0) {
        tbody.innerHTML = '';
        if (empty) empty.style.display = 'block';
        return;
    }
    
    if (empty) empty.style.display = 'none';
    
    tbody.innerHTML = faceAttendanceRecords.map(record => `
        <tr>
            <td><strong>${escapeHtml(record.student_name)}</strong></td>
            <td><span class="badge present"><span class="pulse-dot green"></span> ${record.status}</span></td>
            <td>${formatTime(record.time)}</td>
            <td>${record.confidence}%</td>
            <td><span class="badge active-badge">FACE</span></td>
        </tr>
    `).join('');
}
