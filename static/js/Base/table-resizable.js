(function () {
    /**
     * Resizable Table Columns Logic
     */
    function initResizableTable(table) {
        const cols = table.querySelectorAll('th');
        
        // We no longer set initial widths here to allow CSS-defined layout.
        // The browser will use the 'table-layout: fixed' with the widths provided in CSS.

        cols.forEach((col, index) => {
            if (index === cols.length - 1) return; 
            
            if (col.querySelector('.cf-table__resizer')) return;

            const resizer = document.createElement('div');
            resizer.classList.add('cf-table__resizer');
            
            col.appendChild(resizer);
            
            let startX, startWidth, tableWidth;

            resizer.addEventListener('mousedown', (e) => {
                const currentCols = table.querySelectorAll('th');
                const widths = Array.from(currentCols).map(c => c.offsetWidth);
                
                currentCols.forEach((c, i) => {
                    c.style.width = widths[i] + 'px';
                });
                table.style.tableLayout = 'fixed';
                // Remove 100% width to allow the table to expand naturally when columns are enlarged
                table.style.width = table.offsetWidth + 'px';

                startX = e.pageX;
                startWidth = col.offsetWidth;
                tableWidth = table.offsetWidth;
                resizer.classList.add('is-resizing');
                
                const onMouseMove = (ev) => {
                    const movement = ev.pageX - startX;
                    const newWidth = startWidth + movement;
                    
                    if (newWidth > 60) {
                        col.style.width = newWidth + 'px';
                        table.style.width = (tableWidth + movement) + 'px';
                    }
                };

                const onMouseUp = () => {
                    resizer.classList.remove('is-resizing');
                    document.removeEventListener('mousemove', onMouseMove);
                    document.removeEventListener('mouseup', onMouseUp);
                    document.body.style.userSelect = '';
                };

                document.addEventListener('mousemove', onMouseMove);
                document.addEventListener('mouseup', onMouseUp);
                document.body.style.userSelect = 'none';
            });
        });
    }

    function initAll() {
        const tables = document.querySelectorAll('.cf-table--resizable');
        tables.forEach(initResizableTable);
    }

    // Reset fixed widths on window resize to return to fluid state
    window.addEventListener('resize', () => {
        const tables = document.querySelectorAll('.cf-table--resizable');
        tables.forEach(table => {
            const cols = table.querySelectorAll('th');
            cols.forEach(col => col.style.width = ''); 
            table.style.tableLayout = '';
            table.style.width = '100%';
        });
    });

    window.addEventListener('DOMContentLoaded', initAll);
    window.initResizableTables = initAll;
})();
