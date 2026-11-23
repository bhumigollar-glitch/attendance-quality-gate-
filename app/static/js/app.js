let selectedFile = null;

document.addEventListener("DOMContentLoaded", () => {
    loadRuleVersions();
    loadUploadHistory();
    setupDropzone();
});

async function loadRuleVersions() {
    try {
        const res = await fetch("/rules");
        const data = await res.json();
        const select = document.getElementById("ruleVersion");
        select.innerHTML = "";
        data.available_versions.forEach(v => {
            const opt = document.createElement("option");
            opt.value = v;
            opt.textContent = `${v} (${v === data.default_version ? "Default - Core" : "Extended"})`;
            if (v === data.default_version) opt.selected = true;
            select.appendChild(opt);
        });
    } catch (err) {
        console.error("Failed to load rules:", err);
    }
}

function setupDropzone() {
    const dropzone = document.getElementById("dropzone");
    const fileInput = document.getElementById("fileInput");

    dropzone.addEventListener("click", () => fileInput.click());

    dropzone.addEventListener("dragover", (e) => {
        e.preventDefault();
        dropzone.classList.add("dragover");
    });

    dropzone.addEventListener("dragleave", () => {
        dropzone.classList.remove("dragover");
    });

    dropzone.addEventListener("drop", (e) => {
        e.preventDefault();
        dropzone.classList.remove("dragover");
        if (e.dataTransfer.files.length > 0) {
            handleFileSelected(e.dataTransfer.files[0]);
        }
    });

    fileInput.addEventListener("change", (e) => {
        if (e.target.files.length > 0) {
            handleFileSelected(e.target.files[0]);
        }
    });
}

function handleFileSelected(file) {
    selectedFile = file;
    document.getElementById("fileInfo").textContent = `Selected: ${file.name} (${(file.size / 1024).toFixed(1)} KB)`;
    document.getElementById("uploadBtn").disabled = false;
}

async function uploadAndValidate() {
    if (!selectedFile) return;

    const btn = document.getElementById("uploadBtn");
    btn.disabled = true;
    btn.textContent = "Processing & Validating...";

    const ruleVersion = document.getElementById("ruleVersion").value;
    const formData = new FormData();
    formData.append("file", selectedFile);
    formData.append("rule_version", ruleVersion);

    try {
        const res = await fetch("/uploads", {
            method: "POST",
            body: formData,
        });

        if (!res.ok) {
            const err = await res.json();
            alert(`Upload Failed: ${err.detail || "Server error"}`);
            btn.disabled = false;
            btn.textContent = "Upload & Validate Quality Gate";
            return;
        }

        const data = await res.json();
        renderResults(data);
        loadUploadHistory();
    } catch (err) {
        alert(`Error communicating with backend: ${err.message}`);
    } finally {
        btn.disabled = false;
        btn.textContent = "Upload & Validate Quality Gate";
    }
}

async function renderResults(uploadData) {
    document.getElementById("resultsCard").style.display = "block";
    document.getElementById("resultsCard").scrollIntoView({ behavior: "smooth" });

    // Fetch full report
    const res = await fetch(`/uploads/${uploadData.upload_id}/report`);
    const report = await res.json();

    const banner = document.getElementById("decisionBanner");
    banner.className = `decision-banner decision-${report.decision}`;
    banner.innerHTML = `
        <div>
            <strong>Classification: ${report.decision}</strong>
            <div style="font-size: 13px; font-weight: normal; margin-top: 4px;">
                File: ${report.original_filename} | Rule Set: ${report.rule_version}
            </div>
        </div>
        <div style="font-size: 14px;">${report.processing_time_ms.toFixed(1)} ms</div>
    `;

    // Metrics
    document.getElementById("mTotal").textContent = report.total_rows;
    document.getElementById("mValid").textContent = report.valid_rows;
    document.getElementById("mInvalid").textContent = report.invalid_rows;
    document.getElementById("mErrors").textContent = report.error_count;
    document.getElementById("mWarnings").textContent = report.warning_count;
    document.getElementById("mFailedRules").textContent = report.failed_rule_ids.length;

    // Download button
    const downloadContainer = document.getElementById("downloadContainer");
    if (report.decision === "ACCEPTED" && report.download_available) {
        downloadContainer.innerHTML = `
            <a href="/uploads/${report.upload_id}/download" class="btn btn-success" style="width:100%;">
                ⬇️ Download Cleaned Spreadsheet (.${report.original_filename.split('.').pop()})
            </a>
        `;
    } else {
        downloadContainer.innerHTML = `
            <button class="btn btn-disabled" disabled style="width:100%;">
                🔒 Cleaned Download Blocked (Quarantined File)
            </button>
            <p style="font-size: 12px; color: var(--danger); text-align: center; margin-top: 6px;">
                Quarantined uploads cannot enter downstream reporting until errors are corrected.
            </p>
        `;
    }

    // Issues table
    const issuesBody = document.getElementById("issuesTableBody");
    issuesBody.innerHTML = "";

    if (report.issues.length === 0) {
        issuesBody.innerHTML = `<tr><td colspan="6" style="text-align:center; padding:20px; color: var(--success);">
            🎉 Perfect! Zero errors and zero warnings found.
        </td></tr>`;
        return;
    }

    report.issues.forEach(iss => {
        const row = document.createElement("tr");
        const badgeClass = iss.severity === "BLOCKING" ? "badge-blocking" : "badge-warning";
        row.innerHTML = `
            <td><strong>${iss.row_number !== null ? `Row ${iss.row_number}` : "Schema / File"}</strong></td>
            <td><code>${iss.column_name || "-"}</code></td>
            <td><code style="color:#b91c1c;">${iss.invalid_value || "-"}</code></td>
            <td><span class="badge ${badgeClass}">${iss.rule_id}</span></td>
            <td><span class="badge ${badgeClass}">${iss.severity}</span></td>
            <td>${iss.message}</td>
        `;
        issuesBody.appendChild(row);
    });
}

async function loadUploadHistory() {
    try {
        const res = await fetch("/uploads?limit=10");
        const list = await res.json();
        const historyBody = document.getElementById("historyTableBody");
        historyBody.innerHTML = "";

        if (list.length === 0) {
            historyBody.innerHTML = `<tr><td colspan="7" class="empty-state">No uploads processed yet.</td></tr>`;
            return;
        }

        list.forEach(item => {
            const tr = document.createElement("tr");
            const badgeClass = item.decision === "ACCEPTED" ? "badge" : "badge badge-blocking";
            const badgeStyle = item.decision === "ACCEPTED" ? "background:#ecfdf5; color:#065f46;" : "";
            const timeStr = new Date(item.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

            tr.innerHTML = `
                <td><strong>${item.original_filename}</strong></td>
                <td><span class="${badgeClass}" style="${badgeStyle}">${item.decision || "PENDING"}</span></td>
                <td><code>${item.rule_version}</code></td>
                <td>${item.valid_rows} / ${item.total_rows}</td>
                <td>${item.error_count}</td>
                <td>${timeStr}</td>
                <td>
                    <button class="btn" style="padding:4px 8px; font-size:12px; background:#f1f5f9;" onclick="viewHistoricReport('${item.upload_id}')">View Report</button>
                    ${item.decision === "ACCEPTED" ? `<a href="/uploads/${item.upload_id}/download" class="btn" style="padding:4px 8px; font-size:12px; background:#e0f2fe; color:#0369a1; text-decoration:none;">Download</a>` : ''}
                </td>
            `;
            historyBody.appendChild(tr);
        });
    } catch (err) {
        console.error("Failed to load history:", err);
    }
}

async function viewHistoricReport(uploadId) {
    const res = await fetch(`/uploads/${uploadId}`);
    const data = await res.json();
    renderResults(data);
}
