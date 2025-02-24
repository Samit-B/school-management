// Handle event deletion
document.addEventListener('DOMContentLoaded', function() {
    const deleteButtons = document.querySelectorAll('.delete-event');
    
    deleteButtons.forEach(button => {
        button.addEventListener('click', async function(e) {
            e.preventDefault();
            const eventId = this.dataset.eventId;
            
            try {
                const response = await fetch(`/events/${eventId}`, {
                    method: 'DELETE'
                });
                
                if (response.ok) {
                    // Remove the event from the UI
                    this.closest('.event-item').remove();
                } else {
                    const error = await response.json();
                    alert(error.detail || 'Failed to delete event');
                }
            } catch (error) {
                console.error('Error:', error);
                alert('An error occurred while deleting the event');
            }
        });
    });
});
