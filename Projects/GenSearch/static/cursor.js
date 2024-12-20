// Create the custom cursor element
const cursor = document.createElement('div');
cursor.style.width = '15px';
cursor.style.height = '15px';
cursor.style.borderRadius = '50%';
cursor.style.backgroundColor = '#d4af37'; // Use your accent color
cursor.style.position = 'fixed';
cursor.style.pointerEvents = 'none';
cursor.style.transform = 'translate(-50%, -50%)';
cursor.style.transition = 'background-color 0.3s, transform 0.3s';
cursor.style.zIndex = '9999';
document.body.appendChild(cursor);

// Update cursor position based on mouse movement
document.addEventListener('mousemove', (e) => {
    cursor.style.left = `${e.clientX}px`;
    cursor.style.top = `${e.clientY}px`;
});

// Change cursor color when hovering over buttons or input fields
const interactiveElements = document.querySelectorAll('button, #chat-input');

interactiveElements.forEach((element) => {
    element.addEventListener('mouseenter', () => {
        cursor.style.backgroundColor = '#1a1a40'; // Change color on hover
        cursor.style.transform = 'scale(1.2)'; // Scale up on hover
    });

    element.addEventListener('mouseleave', () => {
        cursor.style.backgroundColor = '#d4af37'; // Reset color
        cursor.style.transform = 'scale(1)'; // Reset scale
    });
});
