class ZillowChatBot {
    constructor() {
        this.chatMessages = document.getElementById('chatMessages');
        this.messageInput = document.getElementById('messageInput');
        this.sendButton = document.getElementById('sendButton');
        this.typingIndicator = document.getElementById('typingIndicator');
        
        this.apiBaseUrl = 'http://localhost:8000';
        
        this.init();
    }
    
    init() {
        this.sendButton.addEventListener('click', () => this.sendMessage());
        this.messageInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.sendMessage();
            }
        });
        
        // Focus input on load
        this.messageInput.focus();
    }
    
    async sendMessage() {
        const message = this.messageInput.value.trim();
        
        if (!message) return;
        
        // Add user message to chat
        this.addMessage(message, 'user');
        
        // Clear input and disable
        this.messageInput.value = '';
        this.setInputState(false);
        
        // Show typing indicator
        this.showTypingIndicator();
        
        try {
            const response = await this.callZillowAPI(message);
            this.hideTypingIndicator();
            this.addBotMessage(response);
        } catch (error) {
            this.hideTypingIndicator();
            this.addErrorMessage(error.message);
        } finally {
            this.setInputState(true);
            this.messageInput.focus();
        }
    }
    
    async callZillowAPI(query) {
        try {
            const response = await fetch(`${this.apiBaseUrl}/chat`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ query })
            });
            
            if (!response.ok) {
                throw new Error(`Server error: ${response.status}`);
            }
            
            const data = await response.json();
            return data;
            
        } catch (error) {
            if (error.name === 'TypeError' && error.message.includes('fetch')) {
                throw new Error('Cannot connect to the server. Please make sure the backend is running on localhost:8000');
            }
            throw error;
        }
    }
    
    addMessage(content, sender) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender}-message`;
        
        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        
        const paragraph = document.createElement('p');
        paragraph.textContent = content;
        contentDiv.appendChild(paragraph);
        
        messageDiv.appendChild(contentDiv);
        this.chatMessages.appendChild(messageDiv);
        
        this.scrollToBottom();
    }
    
    addBotMessage(response) {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message bot-message';
        
        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        
        if (!response.success) {
            // Show error message
            const paragraph = document.createElement('p');
            paragraph.textContent = response.error || 'Something went wrong. Please try again.';
            contentDiv.appendChild(paragraph);
        } else if (response.response_type === 'general_chat') {
            // Handle general chat response
            const paragraph = document.createElement('p');
            paragraph.textContent = response.message || 'I\'m here to help!';
            contentDiv.appendChild(paragraph);
        } else if (response.response_type === 'property_estimate') {
            // Handle property estimate response
            if (response.zestimate) {
                // Create property result card
                const resultCard = this.createPropertyResultCard(response);
                contentDiv.appendChild(resultCard);
                
                // Add conversational response if available
                if (response.conversational_response) {
                    const conversationalDiv = document.createElement('div');
                    const conversationalP = document.createElement('p');
                    conversationalP.textContent = response.conversational_response;
                    conversationalDiv.appendChild(conversationalP);
                    contentDiv.appendChild(conversationalDiv);
                }
            } else {
                // Show no result message for property queries
                const paragraph = document.createElement('p');
                paragraph.textContent = response.error || 'I couldn\'t find property information for that address. Please try with a complete address including city, state, and ZIP code.';
                contentDiv.appendChild(paragraph);
            }
        } else {
            // Fallback for unknown response types
            const paragraph = document.createElement('p');
            paragraph.textContent = 'I received your message but I\'m not sure how to respond. Could you try rephrasing?';
            contentDiv.appendChild(paragraph);
        }
        
        messageDiv.appendChild(contentDiv);
        this.chatMessages.appendChild(messageDiv);
        
        this.scrollToBottom();
    }
    
    createPropertyResultCard(response) {
        const card = document.createElement('div');
        card.className = 'property-result';
        
        const title = document.createElement('h4');
        title.textContent = 'Property Estimate Found';
        card.appendChild(title);
        
        if (response.zestimate) {
            const zestimate = document.createElement('div');
            zestimate.className = 'zestimate';
            zestimate.textContent = `$${response.zestimate.toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`;
            card.appendChild(zestimate);
        }
        
        if (response.address) {
            const address = document.createElement('div');
            address.className = 'address';
            address.textContent = `Address: ${response.address}`;
            card.appendChild(address);
        }
        
        if (response.radius !== undefined) {
            const radius = document.createElement('div');
            radius.className = 'address';
            radius.textContent = `Search radius: ${response.radius} mile(s)`;
            card.appendChild(radius);
        }
        
        return card;
    }
    
    // formatConversationalResponse removed — using textContent for XSS safety
    
    addErrorMessage(errorMessage) {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message bot-message';
        
        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        
        const errorDiv = document.createElement('div');
        errorDiv.className = 'error-message';
        errorDiv.textContent = `Error: ${errorMessage}`;
        contentDiv.appendChild(errorDiv);
        
        messageDiv.appendChild(contentDiv);
        this.chatMessages.appendChild(messageDiv);
        
        this.scrollToBottom();
    }
    
    showTypingIndicator() {
        this.typingIndicator.classList.add('show');
        this.scrollToBottom();
    }
    
    hideTypingIndicator() {
        this.typingIndicator.classList.remove('show');
    }
    
    setInputState(enabled) {
        this.messageInput.disabled = !enabled;
        this.sendButton.disabled = !enabled;
    }
    
    scrollToBottom() {
        this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
    }
}

// Initialize the chat bot when the page loads
document.addEventListener('DOMContentLoaded', () => {
    new ZillowChatBot();
});
