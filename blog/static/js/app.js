// Character counter for post input and bio
document.addEventListener('DOMContentLoaded', function() {
    const postInput = document.querySelector('.post-input');
    const charCount = document.querySelector('.char-count');
    
    if (postInput && charCount) {
        postInput.addEventListener('input', function() {
            const remaining = 280 - this.value.length;
            charCount.textContent = `${remaining} characters remaining`;
            
            if (remaining < 0) {
                charCount.style.color = '#dc2626';
            } else {
                charCount.style.color = '#536471';
            }
        });
    }
    
    // Bio character counter
    const bioInput = document.querySelector('#bio');
    const bioCharCount = document.querySelector('#bio-char-count');
    
    if (bioInput && bioCharCount) {
        // Set initial count
        bioCharCount.textContent = bioInput.value.length;
        
        bioInput.addEventListener('input', function() {
            bioCharCount.textContent = this.value.length;
        });
    }
});

// Debug: Check if script is running
console.log('Script loading...');

// Make functions globally available
window.app = {
    toggleLike: async function(postId, button) {
        try {
            const isLiked = button.getAttribute('data-liked') === 'true';
            const likeCountSpan = button.textContent.trim().split(' ')[1]; // Get the count part
            let currentCount = parseInt(likeCountSpan) || 0;
            
            if (isLiked) {
                // Unlike
                const response = await fetch(`/api/engagements/?post_id=${postId}`);
                if (response.ok) {
                    const engagements = await response.json();
                    const likeEngagement = engagements.find(e => e.type === 'like');
                    if (likeEngagement) {
                        const deleteResponse = await fetch(`/api/engagements/${likeEngagement.id}`, {
                            method: 'DELETE'
                        });
                        if (deleteResponse.ok) {
                            // Update local state
                            button.setAttribute('data-liked', 'false');
                            button.innerHTML = `🤍 ${currentCount - 1}`;
                            button.classList.remove('liked');
                        }
                    }
                }
            } else {
                // Like
                const response = await fetch('/api/engagements/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        post_id: postId,
                        type: 'like'
                    })
                });
                
                if (response.ok) {
                    // Update local state
                    button.setAttribute('data-liked', 'true');
                    button.innerHTML = `❤️ ${currentCount + 1}`;
                    button.classList.add('liked');
                }
            }
        } catch (error) {
            console.error('Error:', error);
            alert('Failed to toggle like');
        }
    },
    
    // Toggle clanked for a post
    toggleClanked: async function(postId, button) {
        try {
            const isClanked = button.getAttribute('data-clanked') === 'true';
            const clankedCountSpan = button.textContent.trim().split(' ')[1]; // Get the count part
            let currentCount = parseInt(clankedCountSpan) || 0;
            
            if (isClanked) {
                // Unclank
                const response = await fetch(`/api/engagements/?post_id=${postId}`);
                if (response.ok) {
                    const engagements = await response.json();
                    const clankedEngagement = engagements.find(e => e.type === 'clanked');
                    if (clankedEngagement) {
                        const deleteResponse = await fetch(`/api/engagements/${clankedEngagement.id}`, {
                            method: 'DELETE'
                        });
                        if (deleteResponse.ok) {
                            // Update local state
                            button.setAttribute('data-clanked', 'false');
                            button.innerHTML = `🤖 ${currentCount - 1}`;
                            button.classList.remove('clanked');
                        }
                    }
                }
            } else {
                // Clank
                const response = await fetch('/api/engagements/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        post_id: postId,
                        type: 'clanked'
                    })
                });
                
                if (response.ok) {
                    // Update local state
                    button.setAttribute('data-clanked', 'true');
                    button.innerHTML = `🤖 ${currentCount + 1}`;
                    button.classList.add('clanked');
                    
                    // Show random "stupid clanker" toast
                    this.showClankedToast();
                }
            }
        } catch (error) {
            console.error('Error:', error);
            alert('Failed to toggle clanked');
        }
    },
    
            // Show random "stupid clanker" toast message
        showClankedToast: function() {
            const messages = [
                "stupid clanker 🤖",
                "what a clanker move 🤖",
                "clanker alert! 🤖",
                "total clanker energy 🤖",
                "clanker moment 🤖",
                "peak clanker behavior 🤖",
                "clanker vibes detected 🤖",
                "certified clanker 🤖",
                "clanker status: achieved 🤖",
                "clanker level: maximum 🤖"
            ];
            
            const randomMessage = messages[Math.floor(Math.random() * messages.length)];
            
            // Create toast element
            const toast = document.createElement('div');
            toast.className = 'clanked-toast';
            toast.textContent = randomMessage;
            
            // Add to page
            document.body.appendChild(toast);
            
            // Show toast
            setTimeout(() => {
                toast.classList.add('show');
            }, 100);
            
            // Remove toast after 3 seconds
            setTimeout(() => {
                toast.classList.remove('show');
                setTimeout(() => {
                    if (toast.parentNode) {
                        toast.parentNode.removeChild(toast);
                    }
                }, 300);
            }, 3000);
        },
        
        // Toggle clanker status
        toggleClankerStatus: async function() {
            try {
                const response = await fetch('/api/toggle-clanker', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    }
                });
                
                if (response.ok) {
                    const data = await response.json();
                    const button = document.getElementById('clanker-toggle');
                    
                    if (data.is_clanker) {
                        button.textContent = '🤖 Clanker';
                        button.classList.add('active');
                    } else {
                        button.textContent = '👤 Regular User';
                        button.classList.remove('active');
                    }
                    
                    // Show feedback
                    this.showToast(data.is_clanker ? '🤖 You are now a clanker!' : '👤 You are now a regular user!', 'success');
                } else {
                    this.showToast('Failed to update clanker status', 'error');
                }
            } catch (error) {
                console.error('Error toggling clanker status:', error);
                this.showToast('Failed to update clanker status', 'error');
            }
        },
        
        // Show general toast message
        showToast: function(message, type = 'info') {
            const toast = document.createElement('div');
            toast.className = `toast toast-${type}`;
            toast.textContent = message;
            
            document.body.appendChild(toast);
            
            setTimeout(() => {
                toast.classList.add('show');
            }, 100);
            
            setTimeout(() => {
                toast.classList.remove('show');
                setTimeout(() => {
                    if (toast.parentNode) {
                        toast.parentNode.removeChild(toast);
                    }
                }, 300);
            }, 3000);
        },
    
    toggleReplyForm: function(postId) {
        const replyForm = document.getElementById(`replyForm${postId}`);
        if (replyForm.style.display === 'none') {
            replyForm.style.display = 'block';
        } else {
            replyForm.style.display = 'none';
        }
    },
    
    submitReply: async function(event, postId) {
        event.preventDefault();
        
        const form = event.target;
        const formData = new FormData(form);
        const content = formData.get('content');
        
        try {
            const response = await fetch('/api/engagements/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    post_id: postId,
                    type: 'reply',
                    content: content
                })
            });
            
            if (response.ok) {
                // Reload page to show new reply
                window.location.reload();
            } else {
                alert('Failed to post reply');
            }
        } catch (error) {
            console.error('Error:', error);
            alert('Failed to post reply');
        }
    },
    
            goToPost: function(postId) {
            saveScrollPosition(); // Save current scroll position
            window.location.href = `/t/${postId}`;
        },
        
        goBackToFeed: function() {
            window.location.href = '/';
        },
        
        goToProfile: function(username) {
            window.location.href = `/u/${username}`;
        },
        
        // Convert @ mentions to clickable links
        processMentions: function(element) {
            if (!element) return;
            
            const text = element.textContent;
            const mentionRegex = /@(\w+)/gi;  // 'i' flag makes it case insensitive
            const processedText = text.replace(mentionRegex, '<a href="/u/$1" class="mention-link">@$1</a>');
            element.innerHTML = processedText;
        },
        
        // Process all mentions on page load
        processAllMentions: function() {
            document.querySelectorAll('.post-content, .reply-content').forEach(element => {
                this.processMentions(element);
            });
        },
        
        // Clear notifications after 1+ second on screen
        clearNotificationsAfterDelay: function() {
            setTimeout(async () => {
                try {
                    const response = await fetch('/api/clear-notifications', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        }
                    });
                    
                    if (response.ok) {
                        // Update notification badge to 0
                        const badge = document.querySelector('.notification-badge');
                        if (badge) {
                            badge.style.display = 'none';
                        }
                    }
                } catch (error) {
                    console.error('Error clearing notifications:', error);
                }
            }, 1000);
        },
        
        // Refresh notifications in background
        refreshNotifications: async function() {
            try {
                const response = await fetch('/api/notification-count');
                if (response.ok) {
                    const data = await response.json();
                    const count = data.count;
                    
                    // Update notification badge
                    const currentBadge = document.querySelector('.notification-badge');
                    const navLink = document.querySelector('a[href="/notifications"]');
                    
                    if (count > 0) {
                        if (currentBadge) {
                            currentBadge.textContent = count;
                            currentBadge.style.display = 'inline-block';
                        } else if (navLink) {
                            // Create new badge if it doesn't exist
                            const newBadge = document.createElement('span');
                            newBadge.className = 'notification-badge';
                            newBadge.textContent = count;
                            navLink.appendChild(newBadge);
                        }
                    } else {
                        // Hide badge if no notifications
                        if (currentBadge) {
                            currentBadge.style.display = 'none';
                        }
                    }
                }
            } catch (error) {
                console.error('Error refreshing notifications:', error);
            }
        }
};

console.log('Script completed, window.app created:', window.app);

// Global utility functions
function formatTime(timestamp) {
    const date = new Date(timestamp);
    const now = new Date();
    const diff = now - date;
    
    const seconds = Math.floor(diff / 1000);
    const minutes = Math.floor(seconds / 60);
    const hours = Math.floor(minutes / 60);
    const days = Math.floor(hours / 24);
    
    if (days > 0) return `${days}d`;
    if (hours > 0) return `${hours}h`;
    if (minutes > 0) return `${minutes}m`;
    return `${seconds}s`;
}

function updateTimestamps() {
    console.log('updateTimestamps called, found elements:', document.querySelectorAll('[data-timestamp]').length);
    document.querySelectorAll('[data-timestamp]').forEach(element => {
        const timestamp = element.getAttribute('data-timestamp');
        if (timestamp) {
            console.log('Converting timestamp:', timestamp, 'to:', formatTime(timestamp));
            element.textContent = formatTime(timestamp);
        }
    });
}

// Update timestamps every minute
setInterval(updateTimestamps, 60000);
console.log('Setting up timestamp updates, will call updateTimestamps after DOM is ready...');

// Wait for DOM to be fully loaded before running updateTimestamps
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM fully loaded, calling updateTimestamps now...');
    updateTimestamps();
    
    // Process @ mentions after timestamps are updated
    if (window.app && window.app.processAllMentions) {
        window.app.processAllMentions();
    }
});

// Scroll position management
function saveScrollPosition() {
    sessionStorage.setItem('scrollPosition', window.scrollY);
}

function restoreScrollPosition() {
    const savedPosition = sessionStorage.getItem('scrollPosition');
    if (savedPosition !== null) {
        window.scrollTo(0, parseInt(savedPosition));
        sessionStorage.removeItem('scrollPosition'); // Clear after restoring
    }
}

// Save scroll position before navigating away
window.addEventListener('beforeunload', saveScrollPosition);

// Restore scroll position when page loads
document.addEventListener('DOMContentLoaded', restoreScrollPosition);
