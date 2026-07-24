// Client-side state for the beneficiary registration funnel.
//
// The collected answers are the single source of truth, kept per-tab in sessionStorage: they
// survive a reload but die with the tab, and are wiped on an explicit exit (close button, or a
// server "funnelReset" trigger on the age-gated dead-ends). The server stays stateless: every
// request carries the whole set of answers accumulated so far, injected here on htmx:configRequest.
document.addEventListener("alpine:init", () => {
    Alpine.data("beneficiaryFunnel", () => ({
        answers: Alpine.$persist({}).using(sessionStorage).as("beneficiary_funnel"),

        init() {
            document.body.addEventListener("htmx:configRequest", (event) => this.sendAnswers(event));
            document.body.addEventListener("funnelReset", () => this.reset());
            document
                .querySelector("[data-funnel-close]")
                ?.addEventListener("click", () => this.reset());
        },

        // Persist the freshly submitted fields, then piggy-back every prior answer on the request.
        sendAnswers(event) {
            const params = event.detail.parameters;
            const control = ["step", "to", "csrfmiddlewaretoken"];
            const stored = { ...this.answers };
            Object.keys(params).forEach((key) => {
                if (!control.includes(key)) stored[key] = params[key];
            });
            this.answers = stored;
            Object.keys(stored).forEach((key) => {
                if (!(key in params)) params[key] = stored[key];
            });
        },

        reset() {
            this.answers = {};
        },
    }));
});
