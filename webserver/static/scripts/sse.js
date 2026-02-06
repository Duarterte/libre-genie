function toolFunction(...parms) {
    console.log("Hello from the tool function!");
    console.log("Parameters:", parms);
    console.log("Type of first parameter:", typeof parms[0]);
}

document.addEventListener("DOMContentLoaded", () => {
    // Replace '/calendar/events' with your actual server-side SSE endpoint
    const eventSource = new EventSource("/sse");

    eventSource.onopen = () => {
        console.log("SSE connection opened.");
    };

    eventSource.onmessage = (event) => {
        console.log("New message received:", event.data);
        
        let message = event.data;
        try {
            message = JSON.parse(event.data);
        } catch (e) {
            console.warn("Could not parse JSON, using raw data.");
        }

        switch (message.command) {
            case "hello":
                // Spread the array directly. No extra JSON.parse needed here.
                toolFunction(...message.parameters);
                break;
            default:
                console.log("No handler for this message.");
        }
    };

    eventSource.onerror = (error) => {
        console.error("SSE error:", error);
        // The browser will automatically attempt to reconnect, but you might want to close on fatal errors
        if (eventSource.readyState === EventSource.CLOSED) {
            console.log("SSE connection closed.");
        }
    };
});

