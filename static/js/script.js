/* Client-side behavior for every page. */

document.addEventListener("DOMContentLoaded", function () {

    // Show flashed backend messages as SweetAlert popups instead of plain bars.
    document.querySelectorAll(".flash-data").forEach(function (node, index) {
        const category = node.dataset.category;
        const message = node.dataset.message;
        const icon = (category === "success") ? "success"
            : (category === "danger") ? "error"
            : (category === "warning") ? "warning"
            : "info";

        Swal.fire({
            title: icon === "success" ? "Success!" : icon === "error" ? "Oops..." : "Notice",
            icon: icon,
            text: message,
            draggable: true,
            grow: "row",
            showConfirmButton: index === document.querySelectorAll(".flash-data").length - 1,
            timer: index === document.querySelectorAll(".flash-data").length - 1 ? 3500 : undefined,
            timerProgressBar: true,
        });
    });

    // Confirm before submitting forms marked for confirmation.
    document.querySelectorAll("form[data-confirm]").forEach(function (form) {
        form.addEventListener("submit", function (event) {
            if (!form.dataset.confirmed) {
                event.preventDefault();
                event.stopImmediatePropagation();
                Swal.fire({
                    title: "Are you sure?",
                    text: form.getAttribute("data-confirm"),
                    icon: "warning",
                    showCancelButton: true,
                    confirmButtonText: "Yes, continue",
                    cancelButtonText: "Cancel",
                    confirmButtonColor: "#1b7a3d",
                }).then(function (result) {
                    if (result.isConfirmed) {
                        form.dataset.confirmed = "1";
                        form.submit();
                    }
                });
            }
        });
    });

    // Mobile: open / close the sidebar.
    const toggle = document.getElementById("sidebarToggle");
    const sidebar = document.getElementById("sidebar");
    if (toggle && sidebar) {
        toggle.addEventListener("click", function () {
            sidebar.classList.toggle("open");
            let backdrop = document.querySelector(".sidebar-backdrop");
            if (sidebar.classList.contains("open")) {
                if (!backdrop) {
                    backdrop = document.createElement("div");
                    backdrop.className = "sidebar-backdrop";
                    backdrop.addEventListener("click", function () {
                        sidebar.classList.remove("open");
                        backdrop.remove();
                    });
                    document.body.appendChild(backdrop);
                }
            } else if (backdrop) {
                backdrop.remove();
            }
        });
    }
});


// ------------------------------------------
// Custom form validation: red field + red
// message under the field (no browser bubble)
// ------------------------------------------

// Find the error message that belongs directly to this field (if any)
function fieldMessage(field) {
    const next = field.nextElementSibling;
    return next && next.classList.contains("invalid-feedback") ? next : null;
}

// Remove the red highlight and this field's message
function clearFieldError(field) {
    field.classList.remove("is-invalid");
    const message = fieldMessage(field);
    if (message) {
        message.remove();
    }
}

// Show a red border on the field and a red message below it
function setFieldError(field, message) {
    clearFieldError(field);
    field.classList.add("is-invalid");

    const feedback = document.createElement("div");
    feedback.className = "invalid-feedback";
    feedback.textContent = message;
    field.insertAdjacentElement("afterend", feedback);
}

// Human-friendly message for a failed HTML5 validation state
function validationMessage(field) {
    if (field.validity.valueMissing) {
        return "Please fill out this, this is required.";
    }
    if (field.type === "email" && field.validity.typeMismatch) {
        return "Please enter a valid email address.";
    }
    if (field.type === "email" && field.validity.patternMismatch) {
        return "Email must end in .com (e.g. name@gmail.com).";
    }
    if (field.validity.tooShort) {
        return `Must be at least ${field.minLength} characters.`;
    }
    return field.validationMessage;
}

// Take over validation for every form (disables the native popup)
document.querySelectorAll("form").forEach(function (form) {
    form.setAttribute("novalidate", "");

    form.addEventListener("submit", function (event) {
        let firstInvalid = null;

        form.querySelectorAll("input, select, textarea").forEach(function (field) {
            if (field.checkValidity()) {
                clearFieldError(field);
            } else {
                setFieldError(field, validationMessage(field));
                if (!firstInvalid) {
                    firstInvalid = field;
                }
            }
        });

        // Block the submit if anything is invalid and focus the first field
        if (firstInvalid) {
            event.preventDefault();
            event.stopImmediatePropagation();
            firstInvalid.focus();
        }
    });

    // Clear a field's error as soon as the user fixes it
    form.addEventListener("input", function (event) {
        if (event.target.checkValidity()) {
            clearFieldError(event.target);
        }
    });
});

// ------------------------------------------
// Offline support (service worker registration)
// ------------------------------------------

if ("serviceWorker" in navigator) {
    window.addEventListener("load", function () {
        navigator.serviceWorker
            .register("/static/sw.js")
            .catch(function (error) {
                console.warn("Offline caching not available:", error);
            });
    });
}
