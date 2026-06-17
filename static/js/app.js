/**
 * 旅行攻略管理器 - 前端应用 v2
 */
(function() {
'use strict';

// ==================== State ====================
const state = {
    trips: [],
    currentTripId: null,
    currentDayIndex: 0,
    currentView: 'overview',
    selectedFile: null,
    todoFilter: 'all',
    uploadedImagePath: null,
    authToken: null,
    username: null,
    userId: null,
    isLoggedIn: false
};

// ==================== DOM Refs ====================
const $ = (s) => document.querySelector(s);
const $$ = (s) => document.querySelectorAll(s);

// ==================== API ====================
const API = {
    async get(url) {
        const r = await fetch(url);
        return r.json();
    },
    async post(url, data = {}) {
        const r = await fetch(url, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(data)
        });
        return r.json();
    },
    async put(url, data = {}) {
        const r = await fetch(url, {
            method: 'PUT',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(data)
        });
        return r.json();
    },
    async del(url) {
        const r = await fetch(url, {method: 'DELETE'});
        return r.json();
    },
    async upload(url, formData) {
        const r = await fetch(url, {method: 'POST', body: formData});
        return r.json();
    }
};

// ==================== Toast ====================
function showToast(msg, type) {
    type = type || 'info';
    var c = $('#toast-container');
    var t = document.createElement('div');
    t.className = 'toast ' + type;
    t.textContent = msg;
    c.appendChild(t);
    setTimeout(function(){ t.style.opacity='0'; t.style.transition='0.3s'; setTimeout(function(){ t.remove(); },300); },3000);
}

// ==================== Modal ====================
function showModal(title, html, onSave, saveLabel){
    saveLabel = saveLabel || '保存';
    var overlay = $('#modal-overlay');
    var content = $('#modal-content');
    content.innerHTML = '<h3>'+title+'</h3>'+html+'<div class="form-actions"><button class="btn-cancel" id="modal-cancel">取消</button><button class="btn-primary" id="modal-save">'+saveLabel+'</button></div>';
    overlay.classList.remove('hidden');
    $('#modal-cancel').onclick = function(){ overlay.classList.add('hidden'); };
    $('#modal-save').onclick = function(){ if(onSave) onSave(); overlay.classList.add('hidden'); };
    overlay.onclick = function(e){ if(e.target===overlay) overlay.classList.add('hidden'); };
}

// Custom confirm dialog (replaces browser confirm)
function showConfirm(title, message, onConfirm, confirmLabel){
    confirmLabel = confirmLabel || '确认';
    var html = '<div style="text-align:center;padding:12px 0;">'+
        '<div style="font-size:42px;margin-bottom:12px;">⚠️</div>'+
        '<p style="font-size:14px;line-height:1.7;color:var(--text-secondary);">'+message+'</p>'+
    '</div>';
    var overlay = $('#modal-overlay');
    var content = $('#modal-content');
    content.innerHTML = '<h3 style="text-align:center;">'+title+'</h3>'+html+
        '<div class="form-actions" style="justify-content:center;">'+
            '<button class="btn-cancel" id="modal-cancel">取消</button>'+
            '<button class="btn-del" id="modal-save" style="min-width:100px;justify-content:center;">'+confirmLabel+'</button>'+
        '</div>';
    overlay.classList.remove('hidden');
    $('#modal-cancel').onclick = function(){ overlay.classList.add('hidden'); };
    $('#modal-save').onclick = function(){ if(onConfirm) onConfirm(); overlay.classList.add('hidden'); };
    overlay.onclick = function(e){ if(e.target===overlay) overlay.classList.add('hidden'); };
}

function getFormData() {
    var data = {};
    $$('#modal-content input, #modal-content textarea, #modal-content select').forEach(function(el){
        if(el.name) data[el.name] = el.value;
    });
    return data;
}

// ==================== Navigation ====================
function switchView(name) {
    state.currentView = name;
    $$('.nav-item').forEach(function(el){ el.classList.remove('active'); });
    $$('.view').forEach(function(v){ v.classList.remove('active'); });
    var nav = document.querySelector('[data-view="'+name+'"]');
    if(nav) nav.classList.add('active');
    var view = $('#view-'+name);
    if(view) view.classList.add('active');

    if(name === 'overview') loadOverview();
    if(name === 'attractions') loadAttractions();
    if(name === 'todos') loadTodos();
}

// Nav item click handlers
$$('.nav-item').forEach(function(item){
    item.addEventListener('click', function(e){
        e.preventDefault();
        switchView(item.getAttribute('data-view'));
    });
});

// ==================== Trip List ====================
async function loadTrips() {
    var result = await API.get('/api/trips');
    if(result.success) {
        state.trips = result.data;
        renderTripList();
    }
}

function renderTripList() {
    var list = $('#trip-list');
    if(!state.trips.length) {
        list.innerHTML = '<div class="empty-hint">暂无攻略<br><small>点击下方按钮创建</small></div>';
        return;
    }
    list.innerHTML = state.trips.map(function(t){
        var isActive = t.id === state.currentTripId;
        return '<div class="trip-list-item'+(isActive?' active':'')+'" data-id="'+t.id+'">'+
            '<span class="trip-icon">🗺️</span>'+
            '<span class="trip-title">'+escHtml(t.title||'未命名攻略')+'</span>'+
            '<span class="trip-date">'+(t.created_at||'').slice(0,10)+'</span>'+
            '<span class="trip-delete" data-del="'+t.id+'">×</span>'+
        '</div>';
    }).join('');

    // Click: select trip
    list.querySelectorAll('.trip-list-item').forEach(function(row){
        row.addEventListener('click', function(e){
            // If clicking delete button
            if(e.target.classList.contains('trip-delete')){
                e.stopPropagation();
                var id = parseInt(e.target.getAttribute('data-del'));
                showConfirm('删除攻略','确定删除这个攻略吗？相关数据将被清除。', function(){
                    API.del('/api/trips/'+id).then(function(){
                        if(state.currentTripId===id) state.currentTripId=null;
                        loadTrips();
                        loadOverview();
                        showToast('攻略已删除','success');
                    });
                });
                return;
            }
            var id = parseInt(row.getAttribute('data-id'));
            state.currentTripId = id;
            state.currentDayIndex = 0;
            renderTripList();
            switchView('overview');
            loadOverview();
        });
    });
}

// ==================== Overview ====================
async function loadOverview() {
    var empty = $('#overview-empty');
    var content = $('#overview-content');

    if(!state.currentTripId) {
        empty.classList.remove('hidden');
        content.classList.add('hidden');
        $('#current-trip-title').textContent = '选择或上传一个攻略';
        updateStats();
        return;
    }

    var result = await API.get('/api/trips/'+state.currentTripId);
    if(!result.success) {
        empty.classList.remove('hidden');
        content.classList.add('hidden');
        return;
    }

    var trip = result.data;
    $('#current-trip-title').textContent = trip.title || '未命名攻略';
    updateStats();

    if(!trip.days || trip.days.length===0) {
        empty.classList.remove('hidden');
        content.classList.add('hidden');
        // If we have an image but no days, show a prompt
        if(trip.image_path) {
            $('#overview-empty').innerHTML = '<div class="empty-state">'+
                '<div class="empty-icon">🖼️</div>'+
                '<h2>攻略图片已上传</h2>'+
                '<p>但未能自动识别文字。请手动输入攻略内容：</p>'+
                '<button class="btn-primary" onclick="switchView(\'upload\')">📝 前往输入文本</button>'+
            '</div>';
        }
        return;
    }

    empty.classList.add('hidden');
    content.classList.remove('hidden');

    if(state.currentDayIndex >= trip.days.length) state.currentDayIndex = 0;

    // Day tabs
    var dayTabs = $('#day-tabs');
    dayTabs.innerHTML = trip.days.map(function(d,i){
        return '<div class="day-tab'+(i===state.currentDayIndex?' active':'')+'" data-idx="'+i+'">'+
            (d.day_title||'第'+d.day_number+'天')+
        '</div>';
    }).join('') + '<div class="day-tab" id="btn-add-day">＋ 添加天</div>';

    dayTabs.querySelectorAll('.day-tab[data-idx]').forEach(function(tab){
        tab.addEventListener('click', function(){
            state.currentDayIndex = parseInt(tab.getAttribute('data-idx'));
            renderTimeline(trip.days[state.currentDayIndex]);
            $$('#day-tabs .day-tab[data-idx]').forEach(function(t){ t.classList.remove('active'); });
            tab.classList.add('active');
        });
    });

    var addDayBtn = $('#btn-add-day');
    if(addDayBtn){
        addDayBtn.addEventListener('click', async function(){
            var dn = trip.days.length + 1;
            await API.post('/api/trips/'+state.currentTripId+'/days', {day_number:dn, day_title:'第'+dn+'天'});
            loadOverview();
            showToast('第'+dn+'天已添加','success');
        });
    }

    renderTimeline(trip.days[state.currentDayIndex]);
}

function renderTimeline(day) {
    var container = $('#timeline-container');
    if(!day || !day.activities || day.activities.length===0) {
        container.innerHTML = '<div class="empty-state"><p>这一天还没有安排</p>'+
            '<button class="btn-primary" id="btn-add-first">＋ 添加活动</button></div>';
        var b = $('#btn-add-first');
        if(b) b.onclick = function(){ showActivityModal(day?day.id:null); };
        return;
    }

    container.innerHTML = day.activities.map(function(a){
        return '<div class="activity-card'+(a.checked?' checked':'')+'" data-aid="'+a.id+'">'+
            '<div class="activity-header">'+
                (a.time_slot?'<span class="activity-time">'+escHtml(a.time_slot)+'</span>':'')+
                '<span class="activity-content">'+escHtml(a.content)+'</span>'+
            '</div>'+
            '<div class="activity-meta">'+
                (a.location?'<span class="activity-location">📍 '+escHtml(a.location)+'</span>':'')+
                '<span class="activity-category '+(a.category||'景点')+'">'+(a.category||'景点')+'</span>'+
                (a.notes?'<span style="font-size:12px;color:var(--text-muted)">📝 '+escHtml(a.notes)+'</span>':'')+
            '</div>'+
            '<div class="activity-actions">'+
                '<button class="btn-sm btn-check" data-toggle="'+a.id+'">'+(a.checked?'↩ 取消完成':'✅ 完成')+'</button>'+
                (a.location?'<button class="btn-sm btn-xhs" data-xhs="'+escAttr(a.location)+'">📕 小红书攻略</button>':'')+
                '<button class="btn-sm btn-edit" data-edit="'+a.id+'">✏️ 编辑</button>'+
                '<button class="btn-sm btn-del" data-del="'+a.id+'">🗑️ 删除</button>'+
            '</div>'+
        '</div>';
    }).join('') + '<div class="activity-card" style="border:2px dashed var(--primary-light);text-align:center;cursor:pointer" id="btn-add-act">'+
        '<span style="color:var(--primary);font-weight:600">＋ 添加活动</span></div>';

    // Event bindings
    container.querySelectorAll('[data-toggle]').forEach(function(b){
        b.addEventListener('click', async function(e){ e.stopPropagation();
            await API.post('/api/activities/'+b.getAttribute('data-toggle')+'/toggle');
            loadOverview();
        });
    });
    container.querySelectorAll('[data-xhs]').forEach(function(b){
        b.addEventListener('click', function(e){ e.stopPropagation();
            openXHSPanel(b.getAttribute('data-xhs'));
        });
    });
    container.querySelectorAll('[data-edit]').forEach(function(b){
        b.addEventListener('click', function(e){ e.stopPropagation();
            var aid = parseInt(b.getAttribute('data-edit'));
            var act = day.activities.find(function(a){ return a.id===aid; });
            if(act) showActivityModal(day.id, act);
        });
    });
    container.querySelectorAll('[data-del]').forEach(function(b){
        b.addEventListener('click', async function(e){ e.stopPropagation();
            showConfirm('删除活动','确定删除这个活动吗？', function(){
                API.del('/api/activities/'+b.getAttribute('data-del')).then(function(){
                    loadOverview();
                    showToast('活动已删除','success');
                });
            });
        });
    });
    var addBtn = $('#btn-add-act');
    if(addBtn) addBtn.onclick = function(){ showActivityModal(day.id); };
}

function showActivityModal(dayId, activity) {
    var isEdit = !!activity;
    showModal(isEdit?'编辑活动':'添加活动',
        '<div class="form-group"><label>时间</label><input name="time_slot" placeholder="如: 09:00 / 上午" value="'+(activity?activity.time_slot||'':'')+'"></div>'+
        '<div class="form-group"><label>内容 *</label><input name="content" placeholder="活动内容" value="'+(activity?escAttr(activity.content):'')+'" required></div>'+
        '<div class="form-group"><label>地点</label><input name="location" placeholder="地点名称" value="'+(activity?activity.location||'':'')+'"></div>'+
        '<div class="form-group"><label>备注</label><input name="notes" placeholder="备注信息" value="'+(activity?activity.notes||'':'')+'"></div>'+
        '<div class="form-group"><label>分类</label><select name="category">'+
            ['景点','餐饮','住宿','交通','购物','其他'].map(function(c){ return '<option value="'+c+'"'+(activity&&activity.category===c?' selected':'')+'>'+c+'</option>'; }).join('')+
        '</select></div>',
        async function(){
            var data = getFormData();
            if(!data.content){ showToast('请输入活动内容','error'); return; }
            if(isEdit){
                await API.put('/api/activities/'+activity.id, data);
            } else {
                await API.post('/api/days/'+dayId+'/activities', data);
            }
            loadOverview();
            showToast(isEdit?'活动已更新':'活动已添加','success');
        }
    );
}

function updateStats() {
    if(!state.currentTripId){
        $('#stat-days').textContent='0';
        $('#stat-activities').textContent='0';
        $('#stat-done').textContent='0';
        return;
    }
    API.get('/api/trips/'+state.currentTripId+'/stats').then(function(r){
        if(r.success){
            $('#stat-days').textContent = r.data.days||0;
            $('#stat-activities').textContent = r.data.total_activities||0;
            $('#stat-done').textContent = r.data.activity_progress||0;
        }
    });
}

// ==================== Upload ====================
(function(){
    var dz = $('#dropzone');
    var fi = $('#file-input');
    var preview = $('#upload-preview');
    var pImg = $('#preview-img');
    var progress = $('#ocr-progress');
    var upBtn = $('#btn-upload');
    var ocrRes = $('#ocr-result-section');

    dz.addEventListener('click', function(){ fi.click(); });
    dz.addEventListener('dragover', function(e){ e.preventDefault(); dz.classList.add('dragover'); });
    dz.addEventListener('dragleave', function(){ dz.classList.remove('dragover'); });
    dz.addEventListener('drop', function(e){ e.preventDefault(); dz.classList.remove('dragover');
        if(e.dataTransfer.files[0]) handleFile(e.dataTransfer.files[0]); });

    fi.addEventListener('change', function(){ if(fi.files[0]) handleFile(fi.files[0]); });

    function handleFile(file) {
        if(!file.type.startsWith('image/')){ showToast('请选择图片文件','error'); return; }
        state.selectedFile = file;
        var reader = new FileReader();
        reader.onload = function(e){
            pImg.src = e.target.result;
            preview.classList.remove('hidden');
            dz.classList.add('hidden');
            upBtn.disabled = false;
        };
        reader.readAsDataURL(file);
    }

    $('#btn-remove-preview').addEventListener('click', function(){
        state.selectedFile = null; fi.value = '';
        preview.classList.add('hidden'); dz.classList.remove('hidden'); upBtn.disabled = true;
    });

    // Upload button - respect auto-OCR preference
    upBtn.addEventListener('click', async function(){
        if(!state.selectedFile) return;

        var autoOcr = getPref('auto_ocr', 'true') !== 'false';
        if(!autoOcr){
            // Just save the image without OCR
            var fd = new FormData();
            fd.append('file', state.selectedFile);
            var result = await API.upload('/api/ocr/upload', fd);
            if(result.success){
                state.currentTripId = result.data.trip_id;
                await loadTrips();
                renderTripList();
                showToast('图片已上传，请手动输入文字','success');
            }
            return;
        }

        upBtn.disabled = true;
        progress.classList.remove('hidden');
        ocrRes.classList.add('hidden');

        var fd = new FormData();
        fd.append('file', state.selectedFile);

        try {
            var result = await API.upload('/api/ocr/upload', fd);
            progress.classList.add('hidden');

            if(!result.success) {
                showToast('上传失败: '+(result.error||'未知错误'), 'error');
                upBtn.disabled = false;
                return;
            }

            var d = result.data;
            state.currentTripId = d.trip_id;
            state.uploadedImagePath = d.image_path;

            // Show OCR result or failure message
            if(d.ocr && d.ocr.success && d.ocr.text) {
                $('#ocr-text-box').textContent = d.ocr.text;
                ocrRes.classList.remove('hidden');
                showToast('文字识别成功！行程已自动生成', 'success');
            } else if(d.ocr && !d.ocr.success) {
                // OCR failed - show the image and prompt for text
                $('#ocr-text-box').textContent = d.ocr.error || 'OCR不可用';
                ocrRes.classList.remove('hidden');

                // Also show a text input area for manual entry
                $('#text-input').value = '';
                $('#text-input').focus();
                showToast('图片已上传，请在下方输入攻略文本', 'warning');
            }

            if(d.parsed) {
                showToast('行程已自动生成！', 'success');
            }

            // Refresh
            await loadTrips();
            renderTripList();
            updateStats();

            // Respect auto-switch preference
            var autoSwitch = getPref('auto_switch', 'true') !== 'false';
            if(d.parsed && autoSwitch) {
                setTimeout(function(){ switchView('overview'); loadOverview(); }, 300);
            }

        } catch(err) {
            progress.classList.add('hidden');
            showToast('上传失败: '+err.message, 'error');
            upBtn.disabled = false;
        }
    });

    // Parse text button
    $('#btn-parse-text').addEventListener('click', async function(){
        var text = $('#text-input').value.trim();
        if(!text){ showToast('请输入攻略文本内容','error'); return; }

        var payload = {text: text};
        if(state.currentTripId) payload.trip_id = state.currentTripId;

        var result = await API.post('/api/ocr/parse-text', payload);
        if(result.success){
            state.currentTripId = result.data.trip_id;
            await loadTrips();
            renderTripList();
            showToast('文本解析完成！共 '+result.data.parsed.days.length+' 天行程', 'success');
            setTimeout(function(){ switchView('overview'); loadOverview(); }, 300);
        } else {
            showToast('解析失败: '+(result.error||'未知错误'), 'error');
        }
    });

    // Reparse OCR text
    $('#btn-reparse-ocr').addEventListener('click', async function(){
        var text = $('#ocr-text-box').textContent.trim();
        if(!text) return;
        var result = await API.post('/api/ocr/parse-text', {text:text, trip_id:state.currentTripId});
        if(result.success){
            showToast('重新解析完成！','success');
            loadOverview();
        }
    });
})();

// ==================== Attractions ====================
async function loadAttractions() {
    var grid = $('#attractions-grid');
    var result = await API.get('/api/attractions');
    if(!result.success || !result.data.length) {
        grid.innerHTML = '<div class="empty-state"><div class="empty-icon">🏷️</div><p>还没有保存的景点</p><p style="font-size:12px">上传攻略后会自动识别和保存景点</p></div>';
        return;
    }
    renderAttractionCards(result.data, grid);
}

function renderAttractionCards(attractions, grid) {
    grid.innerHTML = attractions.map(function(a){
        return '<div class="attraction-card" data-aid="'+a.id+'">'+
            '<div class="attraction-card-header">'+
                '<div style="display:flex;justify-content:space-between;align-items:flex-start;">'+
                    '<div><div class="attraction-name">🏛️ '+escHtml(a.name)+'</div>'+(a.city?'<div class="attraction-city">📍 '+escHtml(a.city)+'</div>':'')+'</div>'+
                    '<button class="btn-del-attr" data-del="'+a.id+'" title="删除此景点" style="background:none;border:none;color:rgba(255,255,255,0.6);font-size:16px;cursor:pointer;padding:2px 6px;">✕</button>'+
                '</div>'+
            '</div>'+
            '<div class="attraction-card-body">'+
                '<div class="attraction-desc">'+escHtml(a.description||'暂无描述')+'</div>'+
                '<div class="attraction-xhs-count">📕 攻略帖已关联</div>'+
            '</div>'+
            '<div class="attraction-card-footer">'+
                '<button class="btn-sm btn-xhs" data-xhs="'+escAttr(a.name)+'">📕 查看攻略</button>'+
            '</div>'+
        '</div>';
    }).join('');

    // Delete attraction handler
    grid.querySelectorAll('.btn-del-attr').forEach(function(b){
        b.addEventListener('click', async function(e){
            e.stopPropagation();
            var id = parseInt(b.getAttribute('data-del'));
            showConfirm('删除景点','确定删除这个景点吗？', function(){
                API.del('/api/attractions/'+id).then(function(resp){
                    if(resp.success){
                        showToast('景点已删除','success');
                        loadAttractions();
                    }
                });
            });
        });
    });

    // XHS button handler
    grid.querySelectorAll('[data-xhs]').forEach(function(b){
        b.addEventListener('click', function(e){ e.stopPropagation(); openXHSPanel(b.getAttribute('data-xhs')); });
    });

    // Card click → open XHS
    grid.querySelectorAll('.attraction-card').forEach(function(card){
        card.addEventListener('click', function(){
            var btn = card.querySelector('[data-xhs]');
            if(btn) openXHSPanel(btn.getAttribute('data-xhs'));
        });
    });
}

// Search
$('#attr-search').addEventListener('input', async function(){
    var q = this.value.trim();
    if(!q){ loadAttractions(); return; }
    var result = await API.get('/api/xiaohongshu/attractions?keyword='+encodeURIComponent(q));
    var grid = $('#attractions-grid');
    if(result.success && result.data.length) {
        var data = result.data.map(function(a){ return {id:a.name, name:a.name, description:a.top_post?a.top_post.title:'', city:'📕 '+a.post_count+' 篇攻略'}; });
        renderAttractionCards(data, grid);
    }
});

$('#btn-search-xhs').addEventListener('click', function(){
    var q = $('#attr-search').value.trim();
    if(q) openXHSPanel(q);
});

// Clear all attractions
window.clearAllAttractions = function(){
    showConfirm('清空景点','确定要清空所有景点记录吗？此操作不可恢复。', function(){
        API.post('/api/attractions/clear').then(function(resp){
            if(resp.success){
                showToast('所有景点已清空','success');
                loadAttractions();
            }
        });
    });
};

// ==================== Xiaohongshu Panel ====================
var xhsSearchHistory = [];
try {
    xhsSearchHistory = JSON.parse(localStorage.getItem('xhs_history')||'[]');
} catch(e){ xhsSearchHistory = []; }

function saveXHSHistory(query){
    query = query.trim();
    if(!query) return;
    // Remove duplicates
    xhsSearchHistory = xhsSearchHistory.filter(function(h){ return h !== query; });
    // Add to front
    xhsSearchHistory.unshift(query);
    // Keep max 10
    if(xhsSearchHistory.length > 10) xhsSearchHistory = xhsSearchHistory.slice(0,10);
    // Save
    localStorage.setItem('xhs_history', JSON.stringify(xhsSearchHistory));
    renderXHSHistory();
}

function renderXHSHistory(){
    var container = $('#xhs-history');
    var tags = $('#xhs-history-tags');
    if(!xhsSearchHistory.length){
        container.style.display = 'none';
        return;
    }
    container.style.display = 'block';
    tags.innerHTML = xhsSearchHistory.map(function(h){
        return '<span class="xhs-tag" style="cursor:pointer;padding:4px 10px;" data-query="'+escAttr(h)+'">🕐 '+escHtml(h)+'</span>';
    }).join('');
    tags.querySelectorAll('.xhs-tag').forEach(function(tag){
        tag.addEventListener('click', function(){
            var q = tag.getAttribute('data-query');
            $('#xhs-search-input').value = q;
            searchXHS(q);
        });
    });
}

$('#btn-clear-history').addEventListener('click', function(){
    xhsSearchHistory = [];
    localStorage.removeItem('xhs_history');
    renderXHSHistory();
});

async function openXHSPanel(query) {
    $('#xhs-panel').classList.remove('hidden');
    $('#xhs-search-input').value = query;
    saveXHSHistory(query);
    await searchXHS(query);
    renderXHSHistory();
}

async function searchXHS(query) {
    var posts = $('#xhs-posts');
    posts.innerHTML = '<div class="empty-hint">搜索中...</div>';

    var result = await API.get('/api/xiaohongshu/search?q='+encodeURIComponent(query));
    if(!result.success || !result.data.length){
        posts.innerHTML = '<div class="empty-hint">未找到相关攻略<br><small>尝试其他关键词</small></div>';
        return;
    }
    // Store posts data for click handlers
    var currentPosts = result.data;
    posts.innerHTML = currentPosts.map(function(p, idx){
        return '<div class="xhs-post-card" data-post-idx="'+idx+'">'+
            '<div class="xhs-post-header"><span class="xhs-post-cover">'+(p.cover||'📕')+'</span><span class="xhs-post-title">'+escHtml(p.title)+'</span><span class="xhs-post-likes">❤️ '+p.likes+'</span></div>'+
            '<div class="xhs-post-author">@'+escHtml(p.author)+'</div>'+
            '<div class="xhs-post-summary">'+escHtml(p.summary||'')+'</div>'+
            (p.tags?'<div class="xhs-post-tags">'+p.tags.map(function(t){return '<span class="xhs-tag">#'+escHtml(t)+'</span>';}).join('')+'</div>':'')+
            '<div class="xhs-post-actions">'+
                '<button class="btn-sm btn-xhs xhs-open-link" data-url="'+escAttr(p.url||_xhsUrl(p.title))+'">🔗 打开链接</button>'+
                '<button class="btn-sm btn-edit xhs-detail-btn" data-idx="'+idx+'">📋 详情</button>'+
            '</div>'+
        '</div>';
    }).join('');

    // "Open link" button → open in browser directly
    posts.querySelectorAll('.xhs-open-link').forEach(function(btn){
        btn.addEventListener('click', function(e){
            e.stopPropagation();
            var url = btn.getAttribute('data-url');
            window.openXHSLink(url);
        });
    });

    // "Detail" button → show detail modal
    posts.querySelectorAll('.xhs-detail-btn').forEach(function(btn){
        btn.addEventListener('click', function(e){
            e.stopPropagation();
            var idx = parseInt(btn.getAttribute('data-idx'));
            showXHSDetailModal(currentPosts[idx]);
        });
    });

    // Also make entire card clickable → show detail modal
    posts.querySelectorAll('.xhs-post-card').forEach(function(card, i){
        card.addEventListener('click', function(e){
            if(e.target.closest('button')) return; // Don't fire if clicking a button
            showXHSDetailModal(currentPosts[i]);
        });
    });

    // Helper to generate XHS URL
    function _xhsUrl(title){
        return 'https://www.xiaohongshu.com/search_result?keyword='+encodeURIComponent(title)+'&type=51';
    }
}

function showXHSDetailModal(post) {
    var searchUrl = post.url || ('https://www.xiaohongshu.com/search_result?keyword='+encodeURIComponent(post.title)+'&type=51');
    var html = '<div style="text-align:center;margin-bottom:12px;">'+
        '<span style="font-size:40px;">'+(post.cover||'📕')+'</span>'+
        '<h3 style="margin-top:6px;">'+escHtml(post.title)+'</h3>'+
        '<p style="color:var(--text-muted);">@'+escHtml(post.author)+' | ❤️ '+post.likes+'</p>'+
    '</div>'+
    '<div style="background:var(--bg-main);border-radius:8px;padding:14px;line-height:1.7;margin-bottom:12px;">'+
        '<p>'+escHtml(post.summary||'暂无详细内容')+'</p>'+
    '</div>'+
    (post.tags?'<div style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:12px;">'+post.tags.map(function(t){return '<span class="xhs-tag">#'+escHtml(t)+'</span>';}).join('')+'</div>':'')+
    '<div style="display:flex;gap:8px;flex-wrap:wrap;">'+
        '<button class="btn-primary" onclick="window.openXHSLink(\''+escAttr(searchUrl)+'\')" style="flex:1;justify-content:center;">🔗 在浏览器中打开</button>'+
        '<button class="btn-sm btn-xhs" onclick="window.openXHSLink(\''+escAttr(searchUrl)+'\')" style="flex:1;justify-content:center;">📕 去小红书查看</button>'+
    '</div>'+
    '<p style="margin-top:10px;font-size:11px;color:var(--text-muted);text-align:center;">点击按钮将在默认浏览器中打开小红书搜索结果</p>';

    showModal('📕 攻略详情', html, null);
    var saveBtn = $('#modal-save');
    if(saveBtn) saveBtn.style.display = 'none';
    var cancelBtn = $('#modal-cancel');
    if(cancelBtn) cancelBtn.textContent = '关闭';
}

// Global function to open XHS link in system browser
window.openXHSLink = function(url) {
    window.open(url, '_blank');
    showToast('正在浏览器中打开小红书...', 'success');
};

$('#btn-close-xhs').addEventListener('click', function(){ $('#xhs-panel').classList.add('hidden'); });
$('#xhs-search-input').addEventListener('keydown', function(e){ if(e.key==='Enter'){ openXHSPanel(e.target.value); } });
$('#btn-xhs-search-go').addEventListener('click', function(){ var q=$('#xhs-search-input').value.trim(); if(q) openXHSPanel(q); });

// XHS sort tabs
var currentXHSSort = 'default';
var currentXHSQuery = '';
$$('.xhs-sort-btn').forEach(function(btn){
    btn.addEventListener('click', function(){
        $$('.xhs-sort-btn').forEach(function(b){ b.classList.remove('active'); });
        btn.classList.add('active');
        currentXHSSort = btn.getAttribute('data-sort');
        if(currentXHSQuery) {
            searchXHSWithSort(currentXHSQuery, currentXHSSort);
        }
    });
});

async function searchXHSWithSort(query, sort){
    currentXHSQuery = query;
    currentXHSSort = sort;
    var posts = $('#xhs-posts');
    posts.innerHTML = '<div class="empty-hint">搜索中...</div>';

    var result = await API.get('/api/xiaohongshu/search?q='+encodeURIComponent(query)+'&sort='+sort+'&limit=20');
    if(!result.success || !result.data.length){
        posts.innerHTML = '<div class="empty-hint">未找到相关攻略<br><small>尝试其他关键词</small></div>';
        return;
    }
    var currentPosts = result.data;
    renderXHSPostCards(currentPosts);
}

function renderXHSPostCards(currentPosts){
    var posts = $('#xhs-posts');
    posts.innerHTML = currentPosts.map(function(p, idx){
        return '<div class="xhs-post-card" data-post-idx="'+idx+'">'+
            '<div class="xhs-post-header"><span class="xhs-post-cover">'+(p.cover||'📕')+'</span><span class="xhs-post-title">'+escHtml(p.title)+'</span><span class="xhs-post-likes">❤️ '+p.likes+'</span></div>'+
            '<div class="xhs-post-author">@'+escHtml(p.author)+'</div>'+
            '<div class="xhs-post-summary">'+escHtml(p.summary||'')+'</div>'+
            (p.tags?'<div class="xhs-post-tags">'+p.tags.map(function(t){return '<span class="xhs-tag">#'+escHtml(t)+'</span>';}).join('')+'</div>':'')+
            '<div class="xhs-post-actions">'+
                '<button class="btn-sm btn-xhs xhs-open-link" data-url="'+escAttr(p.url||_genXhsUrl(p.title))+'">🔗 打开链接</button>'+
                '<button class="btn-sm btn-edit xhs-detail-btn" data-idx="'+idx+'">📋 详情</button>'+
            '</div>'+
        '</div>';
    }).join('');

    posts.querySelectorAll('.xhs-open-link').forEach(function(btn){
        btn.addEventListener('click', function(e){
            e.stopPropagation();
            window.openXHSLink(btn.getAttribute('data-url'));
        });
    });
    posts.querySelectorAll('.xhs-detail-btn').forEach(function(btn){
        btn.addEventListener('click', function(e){
            e.stopPropagation();
            var idx = parseInt(btn.getAttribute('data-idx'));
            showXHSDetailModal(currentPosts[idx]);
        });
    });
    posts.querySelectorAll('.xhs-post-card').forEach(function(card, i){
        card.addEventListener('click', function(e){
            if(e.target.closest('button')) return;
            showXHSDetailModal(currentPosts[i]);
        });
    });

    function _genXhsUrl(title){
        return 'https://www.xiaohongshu.com/search_result?keyword='+encodeURIComponent(title)+'&type=51';
    }
}

// Update searchXHS to use sort and show sort tabs
var origSearchXHS = searchXHS;
searchXHS = function(query){
    currentXHSQuery = query;
    currentXHSSort = 'default';
    $$('.xhs-sort-btn').forEach(function(b){ b.classList.remove('active'); });
    var defaultBtn = document.querySelector('.xhs-sort-btn[data-sort="default"]');
    if(defaultBtn) defaultBtn.classList.add('active');
    $('#xhs-sort-tabs').style.display = 'flex';
    origSearchXHS(query);
};

// Override the original searchXHS in openXHSPanel to also show sort tabs
var origOpenXHSPanel = openXHSPanel;
openXHSPanel = function(query){
    $('#xhs-sort-tabs').style.display = 'flex';
    $$('.xhs-sort-btn').forEach(function(b){ b.classList.remove('active'); });
    var defaultBtn = document.querySelector('.xhs-sort-btn[data-sort="default"]');
    if(defaultBtn) defaultBtn.classList.add('active');
    currentXHSQuery = query;
    currentXHSSort = 'default';
    origOpenXHSPanel(query);
};

// ==================== Settings ====================
$('#btn-open-settings').addEventListener('click', openSettingsModal);

async function openSettingsModal(){
    var configResp = await API.get('/api/config');
    var config = configResp.success ? configResp.data : {};
    var hasKey = config.has_key;
    var apiType = config.api_type || 'openai';

    var modelOptions = apiType === 'anthropic'
        ? ['claude-sonnet-4-6','claude-opus-4-8','claude-haiku-4-5-20251001']
        : ['deepseek-chat','deepseek-reasoner'];

    var html = '<div class="form-group"><label>API Key</label>'+
        '<input name="api_key" type="password" placeholder="sk-..." value="'+(hasKey ? '••••••••' : '')+'">'+
        '<p style="font-size:11px;color:var(--text-muted);margin-top:4px;">'+
            (hasKey ? 'OK: ' + config.key_masked + ' | Enter new key to replace' : 'Not set | Enter key to enable AI')+
        '</p></div>'+
        '<div class="form-group"><label>API Type</label><select name="api_type" id="api-type-select">'+
            '<option value="openai"'+(apiType==='openai'?' selected':'')+'>OpenAI Compatible (DeepSeek/OpenAI)</option>'+
            '<option value="anthropic"'+(apiType==='anthropic'?' selected':'')+'>Anthropic (Claude)</option>'+
        '</select></div>'+
        '<div class="form-group"><label>Model</label><select name="model" id="model-select">'+
            modelOptions.map(function(m){
                return '<option value="'+m+'"'+(config.model===m?' selected':'')+'>'+m+'</option>';
            }).join('')+
        '</select></div>'+
        '<div class="form-group"><label>API Base URL</label>'+
        '<input name="api_base" placeholder="https://api.deepseek.com" value="'+escAttr(config.api_base||'https://api.deepseek.com')+'">'+
        '<p style="font-size:11px;color:var(--text-muted);margin-top:4px;">DeepSeek: https://api.deepseek.com | Anthropic: https://api.anthropic.com</p></div>'+
        '<div style="background:var(--primary-bg);border-radius:8px;padding:12px;margin-top:8px;">'+
            '<p style="font-size:12px;"><b>How to get API Key?</b></p>'+
            '<p style="font-size:11px;color:var(--text-secondary);">DeepSeek: <a href="https://platform.deepseek.com" target="_blank">platform.deepseek.com</a></p>'+
            '<p style="font-size:11px;color:var(--text-secondary);">Anthropic: <a href="https://console.anthropic.com" target="_blank">console.anthropic.com</a></p>'+
        '</div>';

    showModal('Settings', html, async function(){
        var formData = getFormData();
        var payload = {};
        if(formData.api_key && formData.api_key !== '••••••••'){
            payload.api_key = formData.api_key;
        }
        payload.model = formData.model;
        payload.api_base = formData.api_base;
        payload.api_type = formData.api_type;

        var result = await API.put('/api/config', payload);
        if(result.success){
            showToast('Settings saved!','success');
            checkAIStatus();
        }else{
            showToast('Save failed','error');
        }
    });

    // Dynamic model switching based on API type
    document.getElementById('api-type-select').addEventListener('change', function(){
        var type = this.value;
        var modelSelect = document.getElementById('model-select');
        var models = type === 'anthropic'
            ? ['claude-sonnet-4-6','claude-opus-4-8','claude-haiku-4-5-20251001']
            : ['deepseek-chat','deepseek-reasoner'];
        modelSelect.innerHTML = models.map(function(m){
            return '<option value="'+m+'">'+m+'</option>';
        }).join('');
        // Auto-update base URL
        var baseInput = document.querySelector('input[name="api_base"]');
        if(baseInput && baseInput.value === 'https://api.deepseek.com' && type === 'anthropic'){
            baseInput.value = 'https://api.anthropic.com';
        } else if(baseInput && baseInput.value === 'https://api.anthropic.com' && type === 'openai'){
            baseInput.value = 'https://api.deepseek.com';
        }
    });
}

// ==================== AI Assistant ====================
async function checkAIStatus(){
    var configResp = await API.get('/api/config');
    var badge = $('#ai-status-badge');
    if(configResp.success && configResp.data.has_key){
        badge.style.background = 'var(--success-bg)';
        badge.style.color = 'var(--success)';
        badge.textContent = '✅ AI已连接';
    } else {
        badge.style.background = 'var(--warning-bg)';
        badge.style.color = 'var(--warning)';
        badge.textContent = '⚠️ 未配置API';
    }
}

window.addAIMessage = function(text, isUser, mode){
    var chat = $('#ai-chat');
    var msgDiv = document.createElement('div');
    msgDiv.className = 'ai-message ' + (isUser ? 'ai-user' : 'ai-bot');

    // Process markdown-like formatting
    var formatted = text
        .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
        .replace(/\*\*(.+?)\*\*/g, '<b>$1</b>')
        .replace(/\n\n/g, '</p><p>')
        .replace(/\n/g, '<br>')
        .replace(/```([\s\S]*?)```/g, '<pre><code>$1</code></pre>')
        .replace(/`(.+?)`/g, '<code>$1</code>')
        .replace(/^### (.+)$/gm, '<h4>$1</h4>')
        .replace(/^## (.+)$/gm, '<h3>$1</h3>')
        .replace(/^- (.+)$/gm, '<li>$1</li>')
        .replace(/(<li>.*<\/li>)/gs, '<ul>$1</ul>');

    msgDiv.innerHTML = '<div class="ai-avatar">'+(isUser?'👤':'🤖')+'</div>'+
        '<div class="ai-bubble"><p>'+formatted+'</p></div>';

    if(mode && mode !== 'api' && !isUser){
        var note = document.createElement('div');
        note.style.cssText = 'margin-top:8px;font-size:11px;color:var(--text-muted);';
        if(mode === 'no_key'){
            note.textContent = '💡 点击右上角 ⚙️ 配置 API Key 以启用真实 AI 对话';
        } else if(mode === 'fallback'){
            note.textContent = '⚠️ API 调用失败，显示的是离线模式回复。请检查 API Key 和网络。';
        }
        msgDiv.querySelector('.ai-bubble').appendChild(note);
    }

    chat.appendChild(msgDiv);
    chat.scrollTop = chat.scrollHeight;
    return msgDiv;
};

window.addAITyping = function(){
    var chat = $('#ai-chat');
    var typing = document.createElement('div');
    typing.className = 'ai-message ai-bot';
    typing.id = 'ai-typing-indicator';
    typing.innerHTML = '<div class="ai-avatar">🤖</div>'+
        '<div class="ai-bubble"><div class="ai-typing"><span></span><span></span><span></span></div></div>';
    chat.appendChild(typing);
    chat.scrollTop = chat.scrollHeight;
};

window.removeAITyping = function(){
    var indicator = document.getElementById('ai-typing-indicator');
    if(indicator) indicator.remove();
};

async function sendAIMessage(question){
    if(!question.trim()) return;

    addAIMessage(question, true);
    addAITyping();
    $('#ai-input').value = '';
    $('#ai-input').style.height = 'auto';

    try {
        var payload = {question: question};
        if(state.currentTripId) payload.trip_id = state.currentTripId;

        var result = await API.post('/api/ai/ask', payload);
        removeAITyping();

        if(result.success){
            var mode = result.data.mode || 'unknown';
            addAIMessage(result.data.reply, false, mode);

            // Show status based on mode
            if(mode === 'api'){
                var badge = $('#ai-status-badge');
                badge.style.background = 'var(--success-bg)';
                badge.style.color = 'var(--success)';
                badge.textContent = '✅ AI已连接';
            }
        } else {
            addAIMessage('抱歉，出了点问题: '+ (result.error||'未知错误'), false, 'error');
        }
    } catch(err){
        removeAITyping();
        addAIMessage('网络错误，请稍后重试: '+err.message, false, 'error');
    }
}

// AI send button
$('#btn-ai-send').addEventListener('click', function(){
    var q = $('#ai-input').value.trim();
    if(q) sendAIMessage(q);
});

// AI input Enter to send
$('#ai-input').addEventListener('keydown', function(e){
    if(e.key === 'Enter' && !e.shiftKey){
        e.preventDefault();
        var q = $('#ai-input').value.trim();
        if(q) sendAIMessage(q);
    }
});

// AI quick prompt buttons
$$('.ai-prompt-btn').forEach(function(btn){
    btn.addEventListener('click', function(){
        var prompt = btn.getAttribute('data-prompt');
        if(prompt) sendAIMessage(prompt);
    });
});

// Update switchView to handle AI and settings views
var origSwitchView = switchView;
switchView = function(name){
    origSwitchView(name);
    if(name === 'ai'){
        checkAIStatus();
        setTimeout(function(){ $('#ai-input').focus(); }, 200);
    }
    if(name === 'settings'){
        initSettingsPage();
    }
};

// ==================== Settings Page ====================
function initSettingsPage(){
    // Tab switching
    $$('.settings-tab').forEach(function(tab){
        tab.addEventListener('click', function(){
            $$('.settings-tab').forEach(function(t){ t.classList.remove('active'); });
            $$('.settings-panel').forEach(function(p){ p.classList.remove('active'); });
            tab.classList.add('active');
            var panel = document.getElementById('panel-' + tab.getAttribute('data-stab'));
            if(panel) panel.classList.add('active');
        });
    });

    // Load account info
    if(state.username){
        var uEl = document.getElementById('settings-username');
        if(uEl) uEl.value = state.username;
        var idEl = document.getElementById('settings-userid');
        if(idEl) idEl.value = state.userId || '-';
    }

    // Load API config
    API.get('/api/config').then(function(r){
        if(r.success){
            var keyEl = document.getElementById('settings-api-key');
            if(keyEl && r.data.has_key) keyEl.value = r.data.key_masked;
            var typeEl = document.getElementById('settings-api-type');
            if(typeEl) typeEl.value = r.data.api_type || 'openai';
            var modelEl = document.getElementById('settings-model');
            if(modelEl) modelEl.value = r.data.model;
            var baseEl = document.getElementById('settings-api-base');
            if(baseEl) baseEl.value = r.data.api_base;
            updateAPIBadge(r.data.has_key);
        }
    });

    // Load preferences
    var theme = localStorage.getItem('pref_theme') || 'light';
    var defView = localStorage.getItem('pref_default_view') || 'overview';
    var autoOcr = localStorage.getItem('pref_auto_ocr') !== 'false';
    var autoSwitch = localStorage.getItem('pref_auto_switch') !== 'false';

    var tEl = document.getElementById('settings-theme');
    if(tEl) tEl.value = theme;
    var vEl = document.getElementById('settings-default-view');
    if(vEl) vEl.value = defView;
    var oEl = document.getElementById('settings-auto-ocr');
    if(oEl) oEl.checked = autoOcr;
    var sEl = document.getElementById('settings-auto-switch');
    if(sEl) sEl.checked = autoSwitch;

    // Change password
    var cpBtn = document.getElementById('btn-change-pwd');
    if(cpBtn) cpBtn.addEventListener('click', async function(){
        var old = document.getElementById('settings-old-pwd');
        var nw = document.getElementById('settings-new-pwd');
        var nw2 = document.getElementById('settings-new-pwd2');
        var o = old ? old.value : '';
        var n = nw ? nw.value : '';
        var n2 = nw2 ? nw2.value : '';

        if(!o){ showToast('请输入当前密码','error'); return; }
        if(!n || n.length < 4){ showToast('新密码至少4位','error'); return; }
        if(n !== n2){ showToast('两次新密码不一致','error'); return; }

        var resp = await API.post('/api/auth/change-password', {
            token: state.authToken,
            old_password: o,
            new_password: n
        });
        if(resp.success){
            showToast('密码修改成功！','success');
            if(old) old.value = '';
            if(nw) nw.value = '';
            if(nw2) nw2.value = '';
        } else {
            showToast('修改失败：' + (resp.error||'错误'),'error');
        }
    });

    // Password match hint
    var p2El = document.getElementById('settings-new-pwd2');
    if(p2El) p2El.addEventListener('input', function(){
        var p1 = document.getElementById('settings-new-pwd');
        var hint = document.getElementById('settings-pwd-hint');
        if(hint && p1){
            if(!p2El.value){ hint.textContent = ''; }
            else if(p2El.value === p1.value){ hint.textContent = '✓ 密码一致'; hint.style.color = 'var(--success)'; }
            else { hint.textContent = '✗ 密码不一致'; hint.style.color = 'var(--danger)'; }
        }
    });

    // Logout
    var loBtn = document.getElementById('btn-logout-settings');
    if(loBtn) loBtn.addEventListener('click', function(){
        showConfirm('退出登录','确定要退出登录吗？', function(){
            localStorage.removeItem('auth_token');
            state.authToken = null; state.username = null; state.isLoggedIn = false;
            document.getElementById('app-main').style.display = 'none';
            document.getElementById('login-page').style.display = 'flex';
            refreshLoginCaptcha();
            showToast('已退出登录','success');
        });
    });

    // Save API
    var saBtn = document.getElementById('btn-save-api');
    if(saBtn) saBtn.addEventListener('click', async function(){
        var key = document.getElementById('settings-api-key');
        var type = document.getElementById('settings-api-type');
        var model = document.getElementById('settings-model');
        var base = document.getElementById('settings-api-base');
        var payload = {};
        if(key && key.value && key.value.indexOf('****') === -1) payload.api_key = key.value;
        if(type) payload.api_type = type.value;
        if(model) payload.model = model.value;
        if(base) payload.api_base = base.value;

        var resp = await API.put('/api/config', payload);
        if(resp.success){
            showToast('API配置已保存！','success');
            updateAPIBadge(true);
            checkAIStatus();
        } else {
            showToast('保存失败','error');
        }
    });

    // Test API
    var taBtn = document.getElementById('btn-test-api');
    if(taBtn) taBtn.addEventListener('click', async function(){
        taBtn.disabled = true; taBtn.textContent = '测试中...';
        var resp = await API.post('/api/ai/ask', {question:'hi'});
        taBtn.disabled = false; taBtn.textContent = '测试连接';
        if(resp.success && resp.data.mode === 'api'){
            showToast('API连接成功！','success');
            updateAPIBadge(true);
        } else {
            showToast('API连接失败：' + (resp.data?resp.data.mode:'error'),'error');
            updateAPIBadge(false);
        }
    });

    // API type change → update model options
    var atEl = document.getElementById('settings-api-type');
    if(atEl) atEl.addEventListener('change', function(){
        var modelEl = document.getElementById('settings-model');
        if(!modelEl) return;
        var models = atEl.value === 'anthropic'
            ? ['claude-sonnet-4-6','claude-opus-4-8','claude-haiku-4-5-20251001']
            : ['deepseek-chat','deepseek-reasoner'];
        modelEl.innerHTML = models.map(function(m){ return '<option value="'+m+'">'+m+'</option>'; }).join('');
        var baseEl = document.getElementById('settings-api-base');
        if(baseEl){
            if(atEl.value === 'anthropic') baseEl.value = 'https://api.anthropic.com';
            else baseEl.value = 'https://api.deepseek.com';
        }
    });

    // Save preferences on change
    ['settings-theme','settings-default-view'].forEach(function(id){
        var el = document.getElementById(id);
        if(el) el.addEventListener('change', savePreferences);
    });
    ['settings-auto-ocr','settings-auto-switch'].forEach(function(id){
        var el = document.getElementById(id);
        if(el) el.addEventListener('change', savePreferences);
    });

    // Export data
    var exBtn = document.getElementById('btn-export-data');
    if(exBtn) exBtn.addEventListener('click', async function(){
        var resp = await API.get('/api/trips');
        var blob = new Blob([JSON.stringify(resp, null, 2)], {type:'application/json'});
        var a = document.createElement('a');
        a.href = URL.createObjectURL(blob);
        a.download = 'travel_backup_' + new Date().toISOString().slice(0,10) + '.json';
        a.click();
        showToast('数据已导出','success');
    });

    // Clear data
    var clBtn = document.getElementById('btn-clear-data');
    if(clBtn) clBtn.addEventListener('click', async function(){
        showConfirm('清除数据','确定要清除所有数据吗？<br><br>建议先导出数据备份。', function(){
            API.del('/api/trips/clear-all').then(function(resp){
                if(resp.success){
                    showToast('所有数据已清除','success');
                    loadTrips();
                    loadOverview();
                }
            });
        });
    });
}

function updateAPIBadge(hasKey){
    var badge = document.getElementById('api-status-badge');
    if(badge){
        if(hasKey){
            badge.style.background = 'var(--success-bg)';
            badge.style.color = 'var(--success)';
            badge.textContent = '✅ API 已配置';
        } else {
            badge.style.background = 'var(--warning-bg)';
            badge.style.color = 'var(--warning)';
            badge.textContent = '⚠️ 未配置 API Key';
        }
    }
}

function savePreferences(){
    var theme = document.getElementById('settings-theme');
    var defView = document.getElementById('settings-default-view');
    var autoOcr = document.getElementById('settings-auto-ocr');
    var autoSwitch = document.getElementById('settings-auto-switch');

    if(theme){ localStorage.setItem('pref_theme', theme.value); applyTheme(theme.value); }
    if(defView) localStorage.setItem('pref_default_view', defView.value);
    if(autoOcr) localStorage.setItem('pref_auto_ocr', autoOcr.checked);
    if(autoSwitch) localStorage.setItem('pref_auto_switch', autoSwitch.checked);
    showToast('偏好设置已保存','success');
}

function applyTheme(mode){
    document.documentElement.setAttribute('data-theme', mode);
    // Update toggle if on settings page
    var el = document.getElementById('settings-theme');
    if(el) el.value = mode;
}

function getPref(key, def){
    return localStorage.getItem('pref_' + key) || def;
}

// Apply theme on startup
(function(){
    var saved = getPref('theme', 'light');
    applyTheme(saved);
})();

// ==================== Todos ====================
async function loadTodos() {
    if(!state.currentTripId){
        $('#todo-list').innerHTML = '<div class="empty-state"><div class="empty-icon">✅</div><p>请先选择或创建一个攻略</p></div>';
        return;
    }
    var result = await API.get('/api/trips/'+state.currentTripId+'/todos');
    var todos = result.success ? result.data : [];
    var list = $('#todo-list');

    var filtered = todos;
    if(state.todoFilter==='active') filtered = todos.filter(function(t){return !t.done;});
    else if(state.todoFilter==='done') filtered = todos.filter(function(t){return t.done;});
    else if(state.todoFilter==='high') filtered = todos.filter(function(t){return t.priority>=1 && !t.done;});

    var done = todos.filter(function(t){return t.done;}).length;
    var total = todos.length;
    $('#todo-progress-fill').style.width = total ? (done/total*100)+'%' : '0%';
    $('#todo-progress-text').textContent = done+'/'+total+' 已完成';
    $('#todo-badge').textContent = (total-done)||'';

    if(!filtered.length){
        list.innerHTML = '<div class="empty-state"><div class="empty-icon">✅</div><p>'+(state.todoFilter==='done'?'还没有完成的事项':'暂无待办事项，在下方添加')+'</p></div>';
        return;
    }
    list.innerHTML = filtered.map(function(t){
        return '<div class="todo-item'+(t.done?' done':'')+'">'+
            '<div class="todo-checkbox'+(t.done?' checked':'')+'" data-toggle="'+t.id+'">'+(t.done?'✓':'')+'</div>'+
            '<span class="todo-text">'+escHtml(t.content)+'</span>'+
            (t.priority>=1?'<span class="todo-priority high">'+(t.priority===2?'紧急':'重要')+'</span>':'')+
            (t.deadline?'<span style="font-size:12px;color:var(--text-muted)">📅 '+t.deadline+'</span>':'')+
            '<button class="todo-delete" data-del="'+t.id+'">🗑️</button>'+
        '</div>';
    }).join('');

    list.querySelectorAll('.todo-checkbox').forEach(function(cb){
        cb.addEventListener('click', async function(){
            await API.post('/api/todos/'+cb.getAttribute('data-toggle')+'/toggle');
            loadTodos();
        });
    });
    list.querySelectorAll('.todo-delete').forEach(function(b){
        b.addEventListener('click', async function(){
            await API.del('/api/todos/'+b.getAttribute('data-del'));
            loadTodos();
            showToast('待办已删除','success');
        });
    });
}

$$('.todo-filters .filter-btn').forEach(function(b){
    b.addEventListener('click', function(){
        $$('.todo-filters .filter-btn').forEach(function(x){x.classList.remove('active');});
        b.classList.add('active');
        state.todoFilter = b.getAttribute('data-filter');
        loadTodos();
    });
});

$('#btn-add-todo').addEventListener('click', async function(){
    var content = $('#todo-input').value.trim();
    if(!content){ showToast('请输入待办内容','error'); return; }
    if(!state.currentTripId){
        var r = await API.post('/api/trips',{title:'我的旅行计划'});
        state.currentTripId = r.data.id;
        await loadTrips();
        renderTripList();
    }
    var priority = parseInt($('#todo-priority').value);
    await API.post('/api/trips/'+state.currentTripId+'/todos',{content:content, priority:priority});
    $('#todo-input').value = '';
    loadTodos();
    showToast('待办已添加','success');
});
$('#todo-input').addEventListener('keydown', function(e){ if(e.key==='Enter') $('#btn-add-todo').click(); });

// ==================== New Trip ====================
$('#btn-new-trip').addEventListener('click', function(){
    var html = '<div style="text-align:center;padding:8px 0;">'+
        '<div style="font-size:40px;margin-bottom:12px;">🗺️</div>'+
        '<div class="form-group"><label>攻略名称</label>'+
        '<input name="trip_title" placeholder="输入攻略名称" value="我的旅行攻略" style="text-align:center;font-size:15px;">'+
        '</div>'+
        '<p style="font-size:12px;color:var(--text-muted);margin-top:8px;">'+
        '创建后可上传攻略图片或输入行程文本</p>'+
    '</div>';
    showModal('新建攻略', html, async function(){
        var data = getFormData();
        var title = data.trip_title || '我的旅行攻略';
        var r = await API.post('/api/trips',{title:title});
        if(r.success){
            state.currentTripId = r.data.id;
            await loadTrips();
            renderTripList();
            switchView('upload');
            showToast('攻略「'+title+'」已创建，请上传图片或输入文本','success');
        }
    }, '创建');
});

// ==================== PDF Export ====================
$('#btn-export-pdf').addEventListener('click', function(){
    if(!state.currentTripId){
        showToast('请先选择或创建一个攻略','warning');
        return;
    }
    var btn = $('#btn-export-pdf');
    btn.disabled = true;
    btn.textContent = '⏳ 生成中...';

    // Trigger download
    var url = '/api/trips/'+state.currentTripId+'/export/pdf';
    var a = document.createElement('a');
    a.href = url;
    a.download = '';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);

    setTimeout(function(){
        btn.disabled = false;
        btn.textContent = '📄 导出PDF';
        showToast('PDF 下载已开始！','success');
    }, 1000);
});

// ==================== Sidebar ====================
$('#btn-toggle-sidebar').addEventListener('click', function(){
    $('#sidebar').classList.toggle('collapsed');
});

// ==================== Helpers ====================
function escHtml(s){ if(!s) return ''; var d=document.createElement('div'); d.textContent=s; return d.innerHTML; }
function escAttr(s){ if(!s) return ''; return s.replace(/"/g,'&quot;').replace(/'/g,'&#39;'); }

// ==================== Login / Auth ====================
var currentLoginCaptchaId = '';
var currentRegCaptchaId = '';

async function refreshLoginCaptcha(){
    try {
        var resp = await API.get('/api/auth/captcha');
        if(resp && resp.success){
            currentLoginCaptchaId = resp.data.captcha_id;
            var img = document.getElementById('captcha-img');
            if(img) img.src = resp.data.image;
        }
    } catch(e){}
}

async function refreshRegCaptcha(){
    try {
        var resp = await API.get('/api/auth/captcha');
        if(resp && resp.success){
            currentRegCaptchaId = resp.data.captcha_id;
            var img = document.getElementById('reg-captcha-img');
            if(img) img.src = resp.data.image;
        }
    } catch(e){}
}

function setupLoginPage(){
    // Login captcha
    var ci = document.getElementById('captcha-img');
    var ch = document.getElementById('captcha-refresh-hint');
    if(ci) ci.addEventListener('click', refreshLoginCaptcha);
    if(ch) ch.addEventListener('click', refreshLoginCaptcha);

    // Login button
    var bl = document.getElementById('btn-login');
    if(bl) bl.addEventListener('click', handleLogin);

    // Enter key
    var pw = document.getElementById('login-password');
    if(pw) pw.addEventListener('keydown', function(e){ if(e.key==='Enter') handleLogin(); });
    var cp = document.getElementById('login-captcha');
    if(cp) cp.addEventListener('keydown', function(e){ if(e.key==='Enter') handleLogin(); });

    // Link to register page
    var lr = document.getElementById('link-to-register');
    if(lr) lr.addEventListener('click', function(e){
        e.preventDefault();
        document.getElementById('login-page').style.display = 'none';
        document.getElementById('register-page').style.display = 'flex';
        refreshRegCaptcha();
    });

    refreshLoginCaptcha();
}

function setupRegisterPage(){
    // Register captcha
    var rci = document.getElementById('reg-captcha-img');
    var rch = document.getElementById('reg-captcha-hint');
    if(rci) rci.addEventListener('click', refreshRegCaptcha);
    if(rch) rch.addEventListener('click', refreshRegCaptcha);

    // Register button
    var br = document.getElementById('btn-register');
    if(br) br.addEventListener('click', handleRegister);

    // Password match check
    var p2 = document.getElementById('reg-password2');
    if(p2) p2.addEventListener('input', function(){
        var p1 = document.getElementById('reg-password');
        var hint = document.getElementById('pwd-match-hint');
        if(hint){
            if(!p2.value){ hint.textContent = ''; hint.style.color = ''; }
            else if(p1 && p2.value === p1.value){ hint.textContent = '✓ 密码一致'; hint.style.color = 'var(--success)'; }
            else { hint.textContent = '✗ 两次密码不一致'; hint.style.color = 'var(--danger)'; }
        }
    });

    // Enter key
    var rpw = document.getElementById('reg-password2');
    if(rpw) rpw.addEventListener('keydown', function(e){ if(e.key==='Enter') handleRegister(); });
    var rcp = document.getElementById('reg-captcha');
    if(rcp) rcp.addEventListener('keydown', function(e){ if(e.key==='Enter') handleRegister(); });

    // Link back to login
    var ll = document.getElementById('link-to-login');
    if(ll) ll.addEventListener('click', function(e){
        e.preventDefault();
        document.getElementById('register-page').style.display = 'none';
        document.getElementById('login-page').style.display = 'flex';
        refreshLoginCaptcha();
    });
}

async function handleLogin(){
    var un = document.getElementById('login-username');
    var pw = document.getElementById('login-password');
    var cp = document.getElementById('login-captcha');
    var username = un ? un.value.trim() : '';
    var password = pw ? pw.value.trim() : '';
    var captcha = cp ? cp.value.trim() : '';

    if(!username){ showToast('请输入用户名', 'error'); return; }
    if(!password){ showToast('请输入密码', 'error'); return; }
    if(!captcha){ showToast('请输入验证码', 'error'); return; }
    if(!currentLoginCaptchaId){ showToast('验证码已过期，已自动刷新', 'warning'); refreshLoginCaptcha(); return; }

    var btn = document.getElementById('btn-login');
    if(btn){ btn.disabled = true; btn.textContent = '登录中...'; }

    try {
        var resp = await API.post('/api/auth/login', {
            username: username, password: password,
            captcha: captcha, captcha_id: currentLoginCaptchaId
        });
        if(btn){ btn.disabled = false; btn.textContent = '登 录'; }
        if(resp && resp.success){
            onAuthSuccess(resp.data, '欢迎回来，' + resp.data.username + '！');
        } else {
            showToast('登录失败：' + ((resp&&resp.error)||'未知错误'), 'error');
            refreshLoginCaptcha();
            if(cp) cp.value = '';
        }
    } catch(e){
        if(btn){ btn.disabled = false; btn.textContent = '登 录'; }
        showToast('网络错误：' + e.message, 'error');
        refreshLoginCaptcha();
    }
}

async function handleRegister(){
    var un = document.getElementById('reg-username');
    var pw = document.getElementById('reg-password');
    var pw2 = document.getElementById('reg-password2');
    var cp = document.getElementById('reg-captcha');
    var username = un ? un.value.trim() : '';
    var password = pw ? pw.value.trim() : '';
    var password2 = pw2 ? pw2.value.trim() : '';
    var captcha = cp ? cp.value.trim() : '';

    if(!username){ showToast('请输入用户名', 'error'); return; }
    if(username.length < 2 || username.length > 20){ showToast('用户名需要2-20个字符', 'error'); return; }
    if(!password){ showToast('请输入密码', 'error'); return; }
    if(password.length < 4){ showToast('密码至少需要4位', 'error'); return; }
    if(password !== password2){ showToast('两次密码输入不一致', 'error'); return; }
    if(!captcha){ showToast('请输入验证码', 'error'); return; }
    if(!currentRegCaptchaId){ showToast('验证码已过期，已自动刷新', 'warning'); refreshRegCaptcha(); return; }

    var btn = document.getElementById('btn-register');
    if(btn){ btn.disabled = true; btn.textContent = '注册中...'; }

    try {
        var resp = await API.post('/api/auth/register', {
            username: username, password: password,
            captcha: captcha, captcha_id: currentRegCaptchaId
        });
        if(btn){ btn.disabled = false; btn.textContent = '注 册'; }
        if(resp && resp.success){
            onAuthSuccess(resp.data, '注册成功！欢迎，' + resp.data.username + '！');
        } else {
            showToast('注册失败：' + ((resp&&resp.error)||'未知错误'), 'error');
            refreshRegCaptcha();
            if(cp) cp.value = '';
        }
    } catch(e){
        if(btn){ btn.disabled = false; btn.textContent = '注 册'; }
        showToast('网络错误：' + e.message, 'error');
        refreshRegCaptcha();
    }
}

function onAuthSuccess(data, msg){
    state.authToken = data.token;
    state.username = data.username;
    state.userId = data.user_id;
    state.isLoggedIn = true;
    localStorage.setItem('auth_token', data.token);
    document.getElementById('login-page').style.display = 'none';
    document.getElementById('register-page').style.display = 'none';
    document.getElementById('app-main').style.display = 'flex';
    initMainApp();
    showToast(msg, 'success');
}

function showApp(){
    document.getElementById('login-page').style.display = 'none';
    document.getElementById('register-page').style.display = 'none';
    document.getElementById('app-main').style.display = 'flex';
    initMainApp();
}

async function initMainApp(){
    await loadTrips();
    if(state.trips.length > 0){
        state.currentTripId = state.trips[0].id;
        renderTripList();
    }
    checkAIStatus();
    window.switchView = switchView;
    window.openXHSPanel = openXHSPanel;
    window.clearAllAttractions = clearAllAttractions;
    window.extractAIAttractions = extractAIAttractions;

    // Apply default startup view preference
    var defView = getPref('default_view', 'overview');
    switchView(defView);
    if(defView === 'overview' && state.currentTripId){
        loadOverview();
    }
    if(defView === 'todos'){
        loadTodos();
    }
    if(defView === 'attractions'){
        loadAttractions();
    }
}

// ==================== AI Extract Attractions ====================
window.extractAIAttractions = async function(){
    if(!state.currentTripId){
        showToast('请先选择一个攻略','warning');
        return;
    }
    var btn = document.getElementById('btn-extract-ai');
    if(btn){ btn.disabled = true; btn.textContent = 'AI识别中...'; }

    try {
        var resp = await API.post('/api/ocr/'+state.currentTripId+'/extract-attractions');
        if(resp.success){
            showToast('AI识别到 ' + resp.data.found + ' 个景点！','success');
            loadAttractions();
        } else {
            showToast('AI识别失败：' + (resp.error||'未知错误'),'error');
        }
    } catch(e){
        showToast('AI识别出错：'+e.message,'error');
    }
    if(btn){ btn.disabled = false; btn.textContent = '🤖 AI识别景点'; }
};

// ==================== Attractions (updated - color coded + editable) ====================
var _origLoadAttractions = loadAttractions;
loadAttractions = async function(){
    var grid = document.getElementById('attractions-grid');
    var result = await API.get('/api/attractions');
    if(!result.success || !result.data.length) {
        grid.innerHTML = '<div class="empty-state"><div class="empty-icon">🏷️</div><p>还没有保存的景点</p><p style="font-size:12px">上传攻略后使用AI自动识别景点，或手动搜索添加</p></div>';
        return;
    }
    renderAttractionCardsV2(result.data, grid);
};

function renderAttractionCardsV2(attractions, grid){
    var sourceLabels = {'ai_identified':'🤖 AI识别','searched':'🔍 搜索发现','manual':'✏️ 手动添加'};
    grid.innerHTML = attractions.map(function(a){
        var source = a.source || 'manual';
        var desc = a.description || '等待AI生成简介...';
        if(desc.length > 60) desc = desc.substring(0, 58) + '...';
        return '<div class="attraction-card source-'+source+'" data-aid="'+a.id+'">'+
            '<div class="attraction-card-header">'+
                '<span class="source-badge">'+(sourceLabels[source]||source)+'</span>'+
                '<div style="display:flex;justify-content:space-between;align-items:flex-start;">'+
                    '<div><div class="attraction-name">' + escHtml(a.name) + '</div>'+(a.city?'<div class="attraction-city">📍 ' + escHtml(a.city) + '</div>':'')+'</div>'+
                    '<button class="btn-del-attr" data-del="'+a.id+'" title="删除景点" style="background:none;border:none;color:rgba(255,255,255,0.6);font-size:16px;cursor:pointer;padding:2px 6px;">✕</button>'+
                '</div>'+
            '</div>'+
            '<div class="attraction-card-body">'+
                '<div class="attraction-desc" style="font-size:13px;color:var(--text-secondary);line-height:1.7;">' + escHtml(desc) + '</div>'+
                '<div class="attraction-xhs-count">📕 已关联小红书攻略</div>'+
            '</div>'+
            '<div class="attraction-card-footer">'+
                '<button class="btn-sm btn-xhs" data-xhs="'+escAttr(a.name)+'">📕 查看攻略</button>'+
                '<button class="btn-sm btn-edit" data-edit-attr="'+a.id+'">✏️ 编辑</button>'+
            '</div>'+
        '</div>';
    }).join('');

    grid.querySelectorAll('.btn-del-attr').forEach(function(b){
        b.addEventListener('click', function(e){ e.stopPropagation();
            showConfirm('删除景点','确定删除这个景点吗？', function(){
                API.del('/api/attractions/'+b.getAttribute('data-del')).then(function(){
                    loadAttractions();
                    showToast('景点已删除','success');
                });
            });
        });
    });
    grid.querySelectorAll('[data-xhs]').forEach(function(b){
        b.addEventListener('click', function(e){ e.stopPropagation(); openXHSPanel(b.getAttribute('data-xhs')); });
    });
    grid.querySelectorAll('[data-edit-attr]').forEach(function(b){
        b.addEventListener('click', async function(e){ e.stopPropagation();
            var id = parseInt(b.getAttribute('data-edit-attr'));
            var attr = attractions.find(function(a){ return a.id === id; });
            if(attr) showEditAttractionModal(attr);
        });
    });
    grid.querySelectorAll('.attraction-card').forEach(function(card){
        card.addEventListener('click', function(){
            var btn = card.querySelector('[data-xhs]');
            if(btn) openXHSPanel(btn.getAttribute('data-xhs'));
        });
    });
}

function showEditAttractionModal(attr){
    showModal('编辑景点',
        '<div class="form-group"><label>景点名称</label><input name="name" value="'+escAttr(attr.name||'')+'"></div>'+
        '<div class="form-group"><label>所在城市</label><input name="city" value="'+escAttr(attr.city||'')+'"></div>'+
        '<div class="form-group"><label>简介描述</label><textarea name="description" rows="3">'+escHtml(attr.description||'')+'</textarea></div>'+
        '<div class="form-group"><label>分类</label><select name="category">'+
            ['景点','餐饮','住宿','交通','购物'].map(function(c){ return '<option value="'+c+'"'+(attr.category===c?' selected':'')+'>'+c+'</option>'; }).join('')+
        '</select></div>',
        async function(){
            var data = getFormData();
            await API.put('/api/attractions/'+attr.id, data);
            showToast('景点信息已更新','success');
            loadAttractions();
        }
    );
}

// Override search to save searched attractions
var _origAttrSearch = document.getElementById('attr-search');
if(_origAttrSearch){
    _origAttrSearch.addEventListener('keydown', async function(e){
        if(e.key === 'Enter'){
            var q = e.target.value.trim();
            if(q){
                // Save as searched attraction
                var resp = await API.post('/api/attractions/save-searched', {name: q});
                if(resp.success){
                    showToast('saved: ' + q,'success');
                    loadAttractions();
                }
                openXHSPanel(q);
            }
        }
    });
}

// ==================== Startup ====================
(function(){
    function ready(){
        setupLoginPage();
        setupRegisterPage();
        checkSavedAuth();
    }

    if(document.readyState === 'loading'){
        document.addEventListener('DOMContentLoaded', ready);
    } else {
        ready();
    }

    function checkSavedAuth(){
        var savedToken = localStorage.getItem('auth_token');
        if(savedToken){
            fetch('/api/auth/validate', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({token: savedToken})
            }).then(function(r){ return r.json(); }).then(function(data){
                if(data && data.success){
                    state.authToken = savedToken;
                    state.username = data.data.username;
                    state.isLoggedIn = true;
                    showApp();
                }
            }).catch(function(){});
        }
    }
})();

})();
