// Global conversation state
let conversation = [];
let currentConversationId = crypto.randomUUID ? crypto.randomUUID() : Math.random().toString(36).substring(2, 15);

// DOM Elements
const widget = document.getElementById('safety-widget');
const statusText = document.getElementById('safety-status');
const confText = document.getElementById('safety-confidence');
const phaseText = document.getElementById('detected-phase');

const formSender = document.getElementById('form-sender');
const formReceiver = document.getElementById('form-receiver');
const historySender = document.getElementById('history-sender');
const historyReceiver = document.getElementById('history-receiver');

// Metadata Elements
const inputSenderId = document.getElementById('meta-sender-id');
const inputSenderAge = document.getElementById('meta-sender-age');
const inputReceiverAge = document.getElementById('meta-receiver-age');
const inputFriendship = document.getElementById('meta-friendship-days');

// Event Listeners
formSender.addEventListener('submit', (e) => handleMessageSubmit(e, 'Sender'));
formReceiver.addEventListener('submit', (e) => handleMessageSubmit(e, 'Receiver'));

async function handleMessageSubmit(e, user) {
  e.preventDefault();
  const form = e.target;
  const input = form.querySelector('input[type="text"]');
  const fileInput = form.querySelector('input[type="file"]');
  const text = input.value.trim();
  
  let base64Image = null;
  
  if (fileInput.files.length > 0) {
      const file = fileInput.files[0];
      base64Image = await new Promise((resolve) => {
          const reader = new FileReader();
          reader.onloadend = () => resolve(reader.result);
          reader.readAsDataURL(file);
      });
  }
  
  if (!text && !base64Image) return;
  
  // Add to state
  const messageData = { sender: user, text: text };
  if (base64Image) {
      messageData.image_base64 = base64Image;
  }
  conversation.push(messageData);
  
  // Render in both panes
  appendMessageToPane(historySender, user, text, base64Image, user === 'Sender');
  appendMessageToPane(historyReceiver, user, text, base64Image, user === 'Receiver');
  
  // Clear input
  input.value = '';
  fileInput.value = '';
  
  // Trigger Analysis
  analyzeConversation();
}

function appendMessageToPane(pane, senderName, text, imageBase64, isMe) {
  const wrapper = document.createElement('div');
  wrapper.className = `message-wrapper ${isMe ? 'me' : 'other'}`;
  
  const senderLabel = document.createElement('div');
  senderLabel.className = 'message-sender';
  senderLabel.textContent = isMe ? 'You' : senderName;
  
  const bubble = document.createElement('div');
  bubble.className = 'message-bubble';
  
  if (imageBase64) {
      const img = document.createElement('img');
      img.src = imageBase64;
      img.style.maxWidth = '200px';
      img.style.borderRadius = '8px';
      img.style.marginBottom = '5px';
      img.style.display = 'block';
      bubble.appendChild(img);
  }
  
  if (text) {
      const textNode = document.createTextNode(text);
      bubble.appendChild(textNode);
  }
  
  wrapper.appendChild(senderLabel);
  wrapper.appendChild(bubble);
  
  pane.appendChild(wrapper);
  pane.scrollTo({ top: pane.scrollHeight, behavior: 'smooth' });
}

async function analyzeConversation() {
  if (conversation.length === 0) return;
  
  // Set loading state
  widget.className = 'safety-widget loading';
  statusText.textContent = 'ANALYZING...';
  confText.textContent = '';
  
  // Grab Metadata from UI
  const metadata = {
    sender_id: inputSenderId.value.trim() || 'unknown',
    conversation_id: currentConversationId,
    sender_age: parseInt(inputSenderAge.value) || 25,
    receiver_age: parseInt(inputReceiverAge.value) || 25,
    friendship_duration_days: parseInt(inputFriendship.value) || 0
  };
  
  try {
    const response = await fetch('/analyze', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ conversation, metadata })
    });
    
    if (!response.ok) {
      throw new Error(`API error: ${response.status}`);
    }
    
    const result = await response.json();
    updateSafetyWidget(result.risk_level, result.confidence, result.detected_phase, result.ai_judgment, result.threat_category, result.action_recommended);
    
  } catch (err) {
    console.error('Error analyzing conversation:', err);
    widget.className = 'safety-widget';
    statusText.textContent = 'ERROR';
    confText.textContent = 'Check console';
  }
}

const aiJudgmentText = document.getElementById('ai-judgment');
const actionPanel = document.getElementById('action-panel');
const threatCategoryBadge = document.getElementById('threat-category-badge');
const actionRecommendedText = document.getElementById('action-recommended-text');

function updateSafetyWidget(riskLevel, confidence, phase = 'Normal', aiJudgment = '', threatCategory = '', actionRecommended = '') {
  const percent = Math.round(confidence * 100);
  
  widget.className = 'safety-widget';
  phaseText.textContent = `Phase: ${phase}`;
  aiJudgmentText.textContent = aiJudgment || '';

  // Action panel logic
  actionPanel.className = 'action-panel hidden';
  if (riskLevel === 'hazardous' && actionRecommended) {
    actionPanel.classList.remove('hidden');
    actionPanel.classList.remove('warning-panel');
    const label = threatCategory && threatCategory !== 'unknown'
      ? threatCategory.replace(/_/g, ' ').toUpperCase()
      : 'THREAT DETECTED';
    threatCategoryBadge.textContent = label;
    actionRecommendedText.textContent = actionRecommended;
  } else if (riskLevel === 'warning' && actionRecommended) {
    actionPanel.classList.remove('hidden');
    actionPanel.classList.add('warning-panel');
    threatCategoryBadge.textContent = 'ADVISORY';
    actionRecommendedText.textContent = actionRecommended;
  }
  
  if (riskLevel === 'safe') {
    widget.classList.add('safe');
    statusText.textContent = 'SAFE';
  } else if (riskLevel === 'warning') {
    widget.classList.add('warning');
    statusText.textContent = 'WARNING';
  } else if (riskLevel === 'hazardous') {
    widget.classList.add('hazardous');
    statusText.textContent = 'HAZARDOUS';
  } else {
    widget.classList.add('safe');
    statusText.textContent = riskLevel.toUpperCase();
  }
  
  confText.textContent = `Conf: ${percent}%`;
}
