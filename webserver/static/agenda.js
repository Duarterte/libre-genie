// --- AI INTERFACE ---
// The AI will send distinct strings, we just pass them to FullCalendar.
// FullCalendar detects "2026-02-03T03:00:00" automatically.
window.addEventFromAI = function(title, startISO, endISO) {
    if (!window.calendar) return;
    
    window.calendar.addEvent({
        title: title,
        start: startISO, // e.g. "2026-02-03T15:00:00"
        end: endISO      // e.g. "2026-02-03T16:00:00"
    });
    console.log(`AI added event: ${title} at ${startISO}`);
}

document.addEventListener('DOMContentLoaded', function () {
    var section = document.querySelector('.calendar');
    if (!section) {
        console.error("calendar section not found");
        return;
    }
    
    var calendarEl = document.createElement('div');
    calendarEl.id = 'calendar';
    calendarEl.style.width = '100%';
    section.appendChild(calendarEl);

    // Get Auth
    const clientId = localStorage.getItem("client_id");
    const secret = localStorage.getItem("client_secret");
    
    // Construct the endpoint with credentials
    let eventsSource = '';
    if (clientId && secret) {
        eventsSource = `/api/calendar/events?client_id=${encodeURIComponent(clientId)}&secret=${encodeURIComponent(secret)}`;
    } else {
        console.warn("No client credentials found for calendar");
    }

    var calendar = new FullCalendar.Calendar(calendarEl, {
        initialView: 'dayGridMonth',
        height: 'auto',           
        contentHeight: 'auto',
        aspectRatio: 1.35,
        nowIndicator: true,
        
        headerToolbar: {
            left: 'prev,next today',
            center: 'title',
            right: window.innerWidth < 768 ? 'dayGridMonth,timeGridDay' : 'dayGridMonth,timeGridWeek'
        },
        
        navLinks: true, 
        navLinkDayClick: 'timeGridDay',

        // 3. Load from API (fetches from database) with credentials
        events: eventsSource,
        
        dateClick: function(info) {
            calendar.changeView('timeGridDay', info.dateStr);
        },
        eventClick: function(info) {
            info.jsEvent.preventDefault();
            console.log("Event clicked:", info.event.title);
            calendar.changeView('timeGridDay', info.event.start);
        },
        
        windowResize: function(view) {
                    // Adjust toolbar when resizing window
                    if (window.innerWidth < 768) {
                        calendar.setOption('headerToolbar', {
                            left: 'prev,next today',
                            center: 'title',
                            right: 'dayGridMonth,timeGridDay'
                        });
                    } else {
                        calendar.setOption('headerToolbar', {
                            left: 'prev,next today',
                            center: 'title',
                            right: 'dayGridMonth,timeGridWeek'
                        });
                    }
                },
                
                dayMaxEvents: true
            });
            calendar.render();
            
            // Expose calendar to global scope so our window helper works
            window.calendar = calendar;
});