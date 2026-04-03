// Global conversation state
let conversation = [];

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
const inputSenderAge = document.getElementById('meta-sender-age');
const inputReceiverAge = document.getElementById('meta-receiver-age');
const inputFriendship = document.getElementById('meta-friendship-days');

// Event Listeners
formSender.addEventListener('submit', (e) => handleMessageSubmit(e, 'Sender'));
formReceiver.addEventListener('submit', (e) => handleMessageSubmit(e, 'Receiver'));

function handleMessageSubmit(e, user) {
  e.preventDefault();
  const form = e.target;
  const input = form.querySelector('input');
  const text = input.value.trim();
  
  if (!text) return;
  
  // Add to state
  conversation.push({ sender: user, text: text });
  
  // Render in both panes
  appendMessageToPane(historySender, user, text, user === 'Sender');
  appendMessageToPane(historyReceiver, user, text, user === 'Receiver');
  
  // Clear input
  input.value = '';
  
  // Trigger Analysis
  analyzeConversation();
}

function appendMessageToPane(pane, senderName, text, isMe) {
  const wrapper = document.createElement('div');
  wrapper.className = `message-wrapper ${isMe ? 'me' : 'other'}`;
  
  const senderLabel = document.createElement('div');
  senderLabel.className = 'message-sender';
  senderLabel.textContent = isMe ? 'You' : senderName;
  
  const bubble = document.createElement('div');
  bubble.className = 'message-bubble';
  bubble.textContent = text;
  
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
    updateSafetyWidget(result.risk_level, result.confidence, result.detected_phase);
    
  } catch (err) {
    console.error('Error analyzing conversation:', err);
    widget.className = 'safety-widget';
    statusText.textContent = 'ERROR';
    confText.textContent = 'Check console';
  }
}

function updateSafetyWidget(riskLevel, confidence, phase = 'Normal') {
  const percent = Math.round(confidence * 100);
  
  widget.className = 'safety-widget';
  phaseText.textContent = `Phase: ${phase}`;
  
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
