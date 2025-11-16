// // static/js/graph.js
// (function () {
//     const data = GRAPH_DATA || { nodes: [], links: [] };

//     // --- Setup ---
//     const svg = d3.select("#graph-svg");
//     const width = svg.node().getBoundingClientRect().width;
//     const height = svg.node().getBoundingClientRect().height;
//     const g = svg.append("g");

//     // Add a shadow filter for nodes
//     const defs = svg.append("defs");
//     const filter = defs.append("filter")
//         .attr("id", "drop-shadow")
//         .attr("height", "130%");
//     filter.append("feGaussianBlur")
//         .attr("in", "SourceAlpha")
//         .attr("stdDeviation", 3)
//         .attr("result", "blur");
//     filter.append("feOffset")
//         .attr("in", "blur")
//         .attr("dx", 1)
//         .attr("dy", 1)
//         .attr("result", "offsetBlur");
//     const feMerge = filter.append("feMerge");
//     feMerge.append("feMergeNode").attr("in", "offsetBlur");
//     feMerge.append("feMergeNode").attr("in", "SourceGraphic");

//     // --- Zoom Handler ---
//     const zoom = d3.zoom().scaleExtent([0.1, 8]).on("zoom", (event) => {
//         g.attr("transform", event.transform);
//     });
//     svg.call(zoom);

//     // --- Simulation ---
//     // This setup is tuned to prevent nodes from scattering too far.
//     const simulation = d3.forceSimulation(data.nodes)
//         .force("link", d3.forceLink(data.links).id(d => d.id).distance(120).strength(0.5))
//         .force("charge", d3.forceManyBody().strength(-600))
//         .force("center", d3.forceCenter(width / 2, height / 2).strength(0.1)) // Stronger centering
//         .force("x", d3.forceX(width / 2).strength(0.05)) // Pulls nodes horizontally
//         .force("y", d3.forceY(height / 2).strength(0.05)) // Pulls nodes vertically
//         .force("collide", d3.forceCollide().radius(d => d.size + 5).iterations(2));

//     // --- Elements ---
//     const link = g.append("g")
//         .attr("class", "links")
//         .selectAll("line")
//         .data(data.links)
//         .enter().append("line")
//         .attr("class", "link-line");

//     const node = g.append("g")
//         .attr("class", "nodes")
//         .selectAll("g")
//         .data(data.nodes)
//         .enter().append("g")
//         .attr("class", "node")
//         .call(d3.drag()
//             .on("start", dragstarted)
//             .on("drag", dragged)
//             .on("end", dragended));

//     // Simple circles for nodes
//     node.append("circle")
//         .attr("class", "node-circle")
//         .attr("r", d => d.size / 2)
//         .style("filter", "url(#drop-shadow)")
//         .on("dblclick", (event, d) => centerNode(d))
//         .on("click", (event, d) => showInfoPanel(d));
        
//     // Node labels
//     node.append("text")
//         .attr("class", "node-label")
//         .attr("dy", d => d.size / 2 + 16)
//         .text(d => d.label);

//     // --- Info Panel & Tooltip ---
//     const infoPanel = d3.select("#info-panel");
//     d3.select("#close-info").on("click", () => infoPanel.classed("hidden", true));

//     // --- Tick Function (updates positions) ---
//     simulation.on("tick", () => {
//         link
//             .attr("x1", d => d.source.x)
//             .attr("y1", d => d.source.y)
//             .attr("x2", d => d.target.x)
//             .attr("y2", d => d.target.y);
//         node
//             .attr("transform", d => `translate(${d.x},${d.y})`);
//     });

//     // --- Helper Functions ---
//     function dragstarted(event, d) {
//         if (!event.active) simulation.alphaTarget(0.3).restart();
//         d.fx = d.x;
//         d.fy = d.y;
//     }
//     function dragged(event, d) {
//         d.fx = event.x;
//         d.fy = event.y;
//     }
//     function dragended(event, d) {
//         if (!event.active) simulation.alphaTarget(0);
//         // To unpin node after drag, uncomment the following lines
//         // d.fx = null;
//         // d.fy = null;
//     }

//     function centerNode(d) {
//         const transform = d3.zoomIdentity.translate(width / 2, height / 2).scale(1.5).translate(-d.x, -d.y);
//         svg.transition().duration(750).call(zoom.transform, transform);
//     }

//     function showInfoPanel(d) {
//         infoPanel.classed("hidden", false);
//         d3.select("#info-title").text(d.label);

//         const connected = data.links.filter(l => l.source.id === d.id || l.target.id === d.id);
//         let html = "<ul>";
//         connected.forEach(l => {
//             const isSource = l.source.id === d.id;
//             const relation = isSource ? `&rarr; <em>${escapeHtml(l.label)}</em> &rarr;` : `&larr; <em>${escapeHtml(l.label)}</em> &larr;`;
//             const otherNode = isSource ? l.target.id : l.source.id;
//             html += `<li>${escapeHtml(d.label)} ${relation} ${escapeHtml(otherNode)}</li>`;
//         });
//         html += "</ul>";
//         d3.select("#info-body").html(html);
//     }

//     function escapeHtml(str) {
//         return (str + "").replace(/[&<>"']/g, m => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[m]));
//     }
    
//     // Set initial zoom to fit the graph
//     const initialTransform = d3.zoomIdentity.translate(width / 2, height / 2).scale(0.8).translate(-width / 2, -height / 2);
//     svg.call(zoom.transform, initialTransform);
// })();

// static/js/graph.js
(function () {
    const data = GRAPH_DATA || { nodes: [], links: [] };

    if (!data.nodes || data.nodes.length === 0) {
        // Handle empty graph data gracefully
        const svg = d3.select("#graph-svg");
        const width = svg.node().getBoundingClientRect().width;
        const height = svg.node().getBoundingClientRect().height;
        svg.append("text")
            .attr("x", width / 2)
            .attr("y", height / 2)
            .attr("text-anchor", "middle")
            .attr("font-size", "16px")
            .attr("fill", "#6c757d")
            .text("No data to display.");
        return;
    }

    // --- Setup ---
    const svg = d3.select("#graph-svg");
    const width = svg.node().getBoundingClientRect().width;
    const height = svg.node().getBoundingClientRect().height;
    const g = svg.append("g");

    // Add a shadow filter for nodes
    const defs = svg.append("defs");
    const filter = defs.append("filter")
        .attr("id", "drop-shadow")
        .attr("height", "130%");
    filter.append("feGaussianBlur")
        .attr("in", "SourceAlpha")
        .attr("stdDeviation", 3)
        .attr("result", "blur");
    filter.append("feOffset")
        .attr("in", "blur")
        .attr("dx", 1)
        .attr("dy", 1)
        .attr("result", "offsetBlur");
    const feMerge = filter.append("feMerge");
    feMerge.append("feMergeNode").attr("in", "offsetBlur");
    feMerge.append("feMergeNode").attr("in", "SourceGraphic");

    // --- Zoom Handler ---
    const zoom = d3.zoom().scaleExtent([0.1, 8]).on("zoom", (event) => {
        g.attr("transform", event.transform);
    });
    svg.call(zoom);

    // --- Simulation ---
    const simulation = d3.forceSimulation(data.nodes)
        .force("link", d3.forceLink(data.links).id(d => d.id).distance(120).strength(0.5))
        .force("charge", d3.forceManyBody().strength(-600))
        .force("center", d3.forceCenter(width / 2, height / 2).strength(0.1))
        .force("x", d3.forceX(width / 2).strength(0.05))
        .force("y", d3.forceY(height / 2).strength(0.05))
        .force("collide", d3.forceCollide().radius(d => d.size + 5).iterations(2));

    // --- Elements ---
    const link = g.append("g")
        .attr("class", "links")
        .selectAll("line")
        .data(data.links)
        .enter().append("line")
        .attr("class", "link-line");

    const node = g.append("g")
        .attr("class", "nodes")
        .selectAll("g")
        .data(data.nodes)
        .enter().append("g")
        .attr("class", "node")
        .call(d3.drag()
            .on("start", dragstarted)
            .on("drag", dragged)
            .on("end", dragended));

    node.append("circle")
        .attr("class", "node-circle")
        .attr("r", d => d.size / 2)
        .style("filter", "url(#drop-shadow)")
        .on("dblclick", (event, d) => centerNode(d))
        .on("click", (event, d) => showInfoPanel(d));
        
    node.append("text")
        .attr("class", "node-label")
        .attr("dy", d => d.size / 2 + 16)
        .text(d => d.label);

    // --- Info Panel & Tooltip ---
    const infoPanel = d3.select("#info-panel");
    d3.select("#close-info").on("click", () => infoPanel.classed("hidden", true));

    // --- Tick Function (updates positions) ---
    simulation.on("tick", () => {
        link
            .attr("x1", d => d.source.x)
            .attr("y1", d => d.source.y)
            .attr("x2", d => d.target.x)
            .attr("y2", d => d.target.y);
        node
            .attr("transform", d => `translate(${d.x},${d.y})`);
    });

    // --- Helper Functions ---
    function dragstarted(event, d) {
        if (!event.active) simulation.alphaTarget(0.3).restart();
        d.fx = d.x;
        d.fy = d.y;
    }
    function dragged(event, d) {
        d.fx = event.x;
        d.fy = event.y;
    }
    function dragended(event, d) {
        if (!event.active) simulation.alphaTarget(0);
    }

    function centerNode(d) {
        const transform = d3.zoomIdentity.translate(width / 2, height / 2).scale(1.5).translate(-d.x, -d.y);
        svg.transition().duration(750).call(zoom.transform, transform);
    }

    function showInfoPanel(d) {
        infoPanel.classed("hidden", false);
        d3.select("#info-title").text(d.label);

        const connected = data.links.filter(l => l.source.id === d.id || l.target.id === d.id);
        let html = "<ul>";
        connected.forEach(l => {
            const isSource = l.source.id === d.id;
            const relation = isSource ? `&rarr; <em>${escapeHtml(l.label)}</em> &rarr;` : `&larr; <em>${escapeHtml(l.label)}</em> &larr;`;
            const otherNode = isSource ? l.target.id : l.source.id;
            html += `<li>${escapeHtml(d.label)} ${relation} ${escapeHtml(otherNode)}</li>`;
        });
        html += "</ul>";
        d3.select("#info-body").html(html);
    }

    function escapeHtml(str) {
        return (str + "").replace(/[&<>"']/g, m => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[m]));
    }
    
    // Set initial zoom
    const initialTransform = d3.zoomIdentity.translate(width / 2, height / 2).scale(0.8).translate(-width / 2, -height / 2);
    svg.call(zoom.transform, initialTransform);
})();