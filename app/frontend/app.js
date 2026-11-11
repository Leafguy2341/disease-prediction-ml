"use strict";
(() => {
  const form = document.querySelector("#chat-form");
  const input = document.querySelector("#message");
  const messages = document.querySelector("#messages");
  const send = document.querySelector("#send");
  const restart = document.querySelector("#new-chat");
  const readiness = document.querySelector("#readiness");
  let sessionId = null;
  let sequence = 0;
  let pending = null;
  let activeBatchId = null;
  const mode = document.querySelector('#mode-select');
  const model = document.querySelector('#model-select');
  const dialogue = document.querySelector('#dialogue-status');

  function retireQuestions() {
    document.querySelectorAll('.batch-form').forEach(f => f.querySelectorAll('select,button').forEach(e => {e.disabled = true;}));
    document.querySelectorAll('.dialogue-actions button').forEach(e=>{e.disabled=true;});
    activeBatchId = null;
  }

  function renderQuestions(bubble, batch) {
    if (!batch || !Array.isArray(batch.items)) return;
    activeBatchId = batch.batch_id;
    const group = document.createElement('form'); group.className = 'batch-form';
    const selectors = [];
    for (const item of batch.items) {
      const row = document.createElement('div'); row.className = 'batch-row';
      const label = document.createElement('label'); label.textContent = `${item.number}. ${item.text}`;
      const select = document.createElement('select'); select.id = `q-${batch.batch_id}-${item.number}`; label.htmlFor = select.id;
      for (const [value, text] of [['','Chưa trả lời'],['present','Có'],['denied','Không'],['uncertain','Không rõ']]) {
        const option = document.createElement('option'); option.value=value; option.textContent=text; select.append(option);
      }
      if (item.state) {select.value=item.state; select.disabled=item.state!=='uncertain';}
      selectors.push({item, select}); row.append(label,select); group.append(row);
    }
    const note=document.createElement('p'); note.className='batch-note';
    note.textContent='Có thể trả lời từng phần. Chưa trả lời không có nghĩa là không có triệu chứng.';
    const submit=document.createElement('button'); submit.type='submit'; submit.className='batch-send'; submit.textContent='Ghi nhận câu trả lời';
    group.append(note,submit); bubble.append(group);
    group.addEventListener('submit',event=>{
      event.preventDefault(); if(pending || batch.batch_id!==activeBatchId || mode.value!=='offline') return;
      const names={present:'có',denied:'không',uncertain:'không rõ'};
      const answered=selectors.filter(({item,select})=>!select.disabled && select.value && select.value!==item.state);
      if(!answered.length){note.textContent='Hãy chọn ít nhất một câu trả lời, hoặc mô tả thêm bằng ô nhập bên dưới.';return;}
      const text=answered.map(({item,select})=>`${item.number} ${names[select.value]}`).join(', ');
      const display=answered.map(({item,select})=>`${item.text}: ${names[select.value]}`).join('; ');
      append('user',display); requestChat(text,false,batch.batch_id);
    });
    messages.scrollTop=messages.scrollHeight;
  }

  function renderActions(bubble, actions) {
    if(!Array.isArray(actions)) return;
    const box=document.createElement('div'); box.className='dialogue-actions';
    const labels={more:'Hỏi thêm triệu chứng',add:'Tôi muốn bổ sung triệu chứng khác',preview:'Xem kết quả tham khảo hiện tại'};
    for(const action of actions){
      if(!labels[action]) continue;
      const button=document.createElement('button');button.type='button';button.textContent=labels[action];
      button.addEventListener('click',()=>{
        if(pending || mode.value!=='offline') return;
        if(action==='add'){input.focus();input.placeholder='Mô tả thêm hoặc nói rõ điều bạn muốn sửa…';return;}
        append('user',labels[action]);requestChat('',false,null,action);
      });box.append(button);
    }
    bubble.append(box);
  }

  function append(role, text, status = "") {
    const welcome = document.querySelector("#welcome");
    if (welcome) welcome.remove();
    const row = document.createElement("article");
    row.className = `message ${role} ${status === "urgent_redirect" ? "urgent" : status.includes("error") || status === "model_not_ready" ? "error" : ""}`;
    const avatar = document.createElement("span");
    avatar.className = "avatar";
    avatar.setAttribute("aria-hidden", "true");
    avatar.textContent = role === "user" ? "Bạn" : "✳";
    const bubble = document.createElement("div");
    bubble.className = "bubble";
    bubble.textContent = text;
    row.append(avatar, bubble);
    messages.append(row);
    messages.scrollTop = messages.scrollHeight;
    return bubble;
  }

  function renderPrediction(bubble, prediction) {
    if (prediction.result_kind === 'hard_vote_result') {
      const vote=prediction.hard_vote_result;
      if(!vote || !Array.isArray(vote.members) || vote.members.length!==3 || !Number.isInteger(vote.votes) || vote.votes<1 || vote.votes>3) return;
      const box=document.createElement('section');box.className='result-box hard-vote';
      const title=document.createElement('div');title.className='result-title';
      title.textContent='HARD VOTING · '+prediction.model_id;box.append(title);
      const winner=document.createElement('div');winner.className='result-label';
      winner.textContent=prediction.presentation?.display_label || vote.label;box.append(winner);
      const summary=document.createElement('p');summary.textContent=`${vote.votes}/3 phiếu cho nhãn được chọn`+(vote.tie?' · phá hòa theo ưu tiên LR → SVC → KNN':'');box.append(summary);
      for(const member of vote.members){const line=document.createElement('p');line.className='member-vote';line.textContent=`${member.model}: ${member.label}`;box.append(line);}
      const note=document.createElement('p');note.className='result-note';note.textContent=prediction.note;box.append(note);
      bubble.append(box);return;
    }
    if (!Array.isArray(prediction.top3)) return;
    if (!prediction.top3.every(item => typeof item.score_percent === 'number' && Number.isFinite(item.score_percent)
      && item.score_percent >= 0 && item.score_percent <= 100)) {
      bubble.append(document.createTextNode('Điểm tự tin dự đoán không hợp lệ; chưa hiển thị kết quả.'));
      return;
    }
    const decimals = prediction.presentation?.SCORE_DECIMALS ?? 4;
    if (!Number.isInteger(decimals) || decimals < 0 || decimals > 8) return;
    const displayRows = Array.isArray(prediction.presentation?.top3) ? prediction.presentation.top3 : [];
    const box = document.createElement("section");
    box.className = "result-box";
    const title = document.createElement("div");
    title.className = "result-title";
    title.textContent = 'TOP 3 · Điểm mô hình (%) · '+prediction.model_id;
    const evaluation=prediction.presentation?.model_evaluation;
    const benchmark=document.createElement('span');benchmark.className='evaluation-reference';
    const verified=evaluation?.model_id===prediction.model_id && evaluation?.checkpoint_sha256===prediction.checkpoint_sha256
      && typeof evaluation.accuracy==='number' && Number.isFinite(evaluation.accuracy) && evaluation.accuracy>=0 && evaluation.accuracy<=1;
    benchmark.textContent=verified ? ` (Accuracy trên tập test: ${(evaluation.accuracy*100).toFixed(4).replace('.',',')}%)`
      : ' (Accuracy test: chưa xác minh cho checkpoint này)';
    title.append(benchmark);
    box.append(title);
    for (const item of prediction.top3) {
      const row = document.createElement("div"); row.className = "result-row";
      const rank = document.createElement("span"); rank.className = "rank"; rank.textContent = String(item.rank);
      const display = displayRows.find(row => row.class_id === item.class_id && row.canonical_label === item.label);
      const label = document.createElement("div"); label.className = "result-label";
      label.textContent = ['reviewed', 'draft'].includes(display?.translation_status) ? display.display_label : item.label;
      label.title = item.label;
      if (label.textContent !== item.label) {
        const canonical=document.createElement('small'); canonical.className='canonical-label'; canonical.textContent=item.label; label.append(canonical);
      }
      const score = document.createElement("span"); score.className = "score";
      const format = new RegExp(decimals ? `^\\d+\\.\\d{${decimals}}%$` : '^\\d+%$');
      // Server formatting is authoritative, including exact half-way rounding.
      score.textContent = typeof display?.score_text === 'string' && format.test(display.score_text)
        ? display.score_text : `${item.score_percent.toFixed(decimals)}%`;
      label.append(score); row.append(rank, label); box.append(row);
    }
    const note = document.createElement("p"); note.className = "result-note";
    note.textContent = "Nhãn gốc được giữ trong metadata. Ba điểm được giữ nguyên, không cộng lại thành 100%.";
    note.textContent+=' '+(prediction.presentation?.confidence_note || 'Điểm tự tin là score chưa calibration, không phải xác suất mắc bệnh.');
    if(verified)note.textContent+=' Accuracy là metric toàn tập test đã đánh giá, không phải độ chính xác của mỗi gợi ý hoặc hiệu năng trên bệnh nhân thật.';
    if (Array.isArray(prediction.presentation?.warnings)) note.textContent += ' ' + prediction.presentation.warnings.join(' ');
    box.append(note); bubble.append(box); messages.scrollTop = messages.scrollHeight;
  }

  async function checkHealth() {
    try {
      const response = await fetch("/health", {cache: "no-store"});
      const body = await response.json();
      const ready = response.ok && body.chat && (body.chat.mode === "offline" || (body.chat.live_enabled && body.chat.key_configured));
      readiness.className = ready ? "readiness ready" : "readiness blocked";
      readiness.textContent = mode.value==='llm' ? 'Online UI chưa hỗ trợ kết nối · LIVE NOT VERIFIED. Chọn Offline để trò chuyện.' : ready && body.chat.mode === "offline" ? body.chat.message : ready ? "Provider được cấu hình trên server; LIVE NOT VERIFIED trong phiên này." : response.ok ? "Chức năng hiểu ngôn ngữ chưa sẵn sàng. Hiện chưa thể tạo gợi ý." : "Mô hình chưa sẵn sàng trên máy chủ. Hiện chưa thể tạo gợi ý.";
      const registry=await (await fetch('/api/v1/models',{cache:'no-store'})).json();
      const selected=model.value;
      if(Array.isArray(registry.models)){
        model.replaceChildren();
        for(const item of registry.models){
          const option=document.createElement('option');option.value=item.model_id;
          option.textContent=item.display_name+(item.available?'':' — BLOCKED: '+(item.reason?.code || 'not_verified'));
          option.disabled=!item.available;model.append(option);
        }
        model.value=selected;
      }
      const entry=registry.models?.find(e=>e.model_id===model.value);
      model.disabled=!registry.models?.some(e=>e.available);
      document.querySelector('#model-help').textContent=entry?.available ? `Đang chọn: ${entry.display_name}. Đổi model sẽ bắt đầu phiên mới.` : 'Model được chọn chưa sẵn sàng: '+(entry?.reason?.message || 'chưa xác minh')+' Không có model thay thế ngầm.';
      send.disabled=!entry?.available || mode.value!=='offline';
    } catch (_) {
      readiness.className = "readiness blocked";
      readiness.textContent = "Chưa kết nối được máy chủ. Hãy kiểm tra ứng dụng localhost.";
    }
  }

  async function requestChat(message, reset = false, batchId = null, action='message') {
    if(mode.value!=='offline') return;
    const current = ++sequence;
    const requestedModel=model.value;
    const previousSessionId = sessionId;
    if (pending) pending.abort();
    pending = new AbortController();
    if (reset) { sessionId = null; messages.replaceChildren(); }
    send.disabled = true;
    retireQuestions();
    if(!reset) document.querySelectorAll('.result-box').forEach(e=>{e.classList.add('historical-result');e.setAttribute('aria-label','Kết quả của lượt trước');});
    try {
      const response = await fetch("/api/v1/chat", {method: "POST", headers: {"Content-Type": "application/json"},
        body: JSON.stringify({message, session_id: previousSessionId, reset, mode:'offline', model_id:requestedModel, batch_id:batchId,action}), signal: pending.signal});
      const body = await response.json();
      if (current !== sequence) return;
      if (body.error) {
        append("assistant", body.error.message || "Yêu cầu chưa xử lý được. Vui lòng thử lại.", "error");
        return;
      }
      sessionId = body.session_id || null;
      const bubble = append("assistant", body.pending_questions ? body.message.split('\n')[0] : body.message, body.status);
      renderQuestions(bubble,body.pending_questions);
      dialogue.textContent=body.dialogue ? `${body.dialogue.present_count} có · ${body.dialogue.denied_count} không · ${body.dialogue.uncertain_count} chưa rõ · ${body.dialogue.answered_questions}/${body.dialogue.asked_questions} câu · vòng ${body.dialogue.question_round}` : body.status==='new_session' ? 'Cuộc trò chuyện mới' : 'Đã cập nhật';
      if (body.status === "prediction_ready" && body.predictions) {
        if(body.predictions.model_id!==requestedModel){bubble.append(document.createTextNode('Model phản hồi không khớp model đã chọn; không hiển thị kết quả.'));return;}
        renderPrediction(bubble, body.predictions);
      }
      renderActions(bubble,body.available_actions);
      if (body.reason === "invalid_session") sessionId = null;
    } catch (error) {
      if (error.name !== "AbortError" && current === sequence) append("assistant", "Kết nối bị gián đoạn. Chưa có kết quả cho lượt này; hãy thử lại.", "error");
    } finally {
      if (current === sequence) { pending = null; send.disabled = mode.value!=='offline'; input.focus(); }
    }
  }

  form.addEventListener("submit", event => {
    event.preventDefault();
    const text = input.value.trim();
    if (!text || pending) return;
    append("user", text); input.value = ""; requestChat(text);
  });
  input.addEventListener("keydown", event => {
    if (event.key === "Enter" && !event.shiftKey && !event.isComposing) { event.preventDefault(); form.requestSubmit(); }
  });
  restart.addEventListener("click", () => { input.value = ""; requestChat("", true); });
  mode.addEventListener('change',()=>{
    if(pending) pending.abort(); ++sequence; pending=null; retireQuestions();
    send.disabled=mode.value!=='offline'; input.disabled=mode.value!=='offline';
    document.querySelector('#mode-help').textContent=mode.value==='offline' ? 'Không cần API key. Không gửi nội dung ra dịch vụ bên ngoài.' : 'Chỉ xem cài đặt. Chưa có luồng lưu key/kết nối qua UI; không gửi hội thoại online.';
    checkHealth();
    if(mode.value==='offline') requestChat('',true);
  });
  model.addEventListener('change',()=>{
    document.querySelector('#model-help').textContent='Đang chọn: '+model.selectedOptions[0].textContent+'. Đang tạo phiên mới.';
    requestChat('',true);
  });
  const settings=document.querySelector('#settings-dialog');
  document.querySelector('#settings-open').addEventListener('click',()=>settings.showModal());
  settings.addEventListener('close',()=>{document.querySelector('#api-key').value='';});
  document.querySelectorAll("[data-example]").forEach(button => button.addEventListener("click", () => {
    input.value = button.dataset.example; input.focus();
  }));
  checkHealth();
})();
