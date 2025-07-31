// Test JavaScript file for syntax highlighting

function greetUser(name) {
    console.log(`Hello, ${name}! Welcome to Text IDE.`);
    
    const currentTime = new Date();
    const timeString = currentTime.toLocaleTimeString();
    
    return {
        message: `Hello ${name}`,
        timestamp: timeString,
        success: true
    };
}

// Test object
const config = {
    theme: 'dark',
    autoSave: true,
    language: 'javascript'
};

// Export for testing
export { greetUser, config };