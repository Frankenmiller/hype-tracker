document.getElementById('searchInput').addEventListener('input', function(e) {
    const query = e.target.value.toLowerCase().trim();
    const cards = document.querySelectorAll('#tracker-card');
    
    cards.forEach(card => {
        const searchContent = card.getAttribute('data-search');
        // If query matches any part of title, reason, or tag, show it. Otherwise, hide it.
        if (searchContent.includes(query)) {
            card.style.display = 'flex';
        } else {
            card.style.display = 'none';
        }
    });
});