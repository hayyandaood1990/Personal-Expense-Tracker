frappe.pages["category-budget-dashboard"].on_page_load = function (wrapper) {
	frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Category Budget Dashboard"),
		single_column: true,
	});

	wrapper.category_budget_dashboard = new CategoryBudgetDashboard(wrapper);
};

frappe.pages["category-budget-dashboard"].on_page_show = function (wrapper) {
	wrapper.category_budget_dashboard?.refresh();
};

class CategoryBudgetDashboard {
	constructor(wrapper) {
		this.wrapper = wrapper;
		this.page = wrapper.page;
		this.data = {};
		this.filters = {
			period: "",
			category: "",
			status: "",
			search: "",
			sort: "usage",
		};

		this.make();
		this.bind();
		this.refresh();
	}

	make() {
		this.page.set_primary_action(__("Refresh"), () => this.refresh(), "refresh");
		this.page.set_secondary_action(__("Open Website Dashboard"), () => {
			window.open("/expense-tracker", "_blank");
		});

		this.container = $(
			`<div class="pet-desk-budget-page">
				<style>${this.get_styles()}</style>
				<section class="pet-desk-budget-hero">
					<div>
						<p>${__("Budget Control")}</p>
						<h2>${__("Category Budget Dashboard")}</h2>
						<span>${__("Monthly Budget records drive active budget usage. Expense Category monthly budgets are shown only as defaults when no active Monthly Budget exists.")}</span>
					</div>
					<div class="pet-desk-budget-period"></div>
				</section>
				<section class="pet-desk-budget-summary"></section>
				<section class="pet-desk-budget-filters">
					<label><span>${__("Budget Period")}</span><select data-filter="period"></select></label>
					<label><span>${__("Category")}</span><select data-filter="category"></select></label>
					<label><span>${__("Status")}</span><select data-filter="status"></select></label>
					<label><span>${__("Sort")}</span><select data-filter="sort">
						<option value="usage">${__("Highest usage")}</option>
						<option value="remaining">${__("Lowest remaining")}</option>
						<option value="overrun">${__("Highest overrun")}</option>
						<option value="category">${__("Category name")}</option>
					</select></label>
					<label><span>${__("Search")}</span><input data-filter="search" type="search" placeholder="${__("Search category or insight")}"></label>
				</section>
				<div class="pet-desk-budget-state text-muted">${__("Loading category budgets...")}</div>
				<section class="pet-desk-budget-grid"></section>
			</div>`
		).appendTo($(this.wrapper).find(".page-content").empty());
	}

	bind() {
		this.container.on("change", "[data-filter='period']", (event) => {
			this.filters.period = event.currentTarget.value;
			this.refresh();
		});
		this.container.on("change", "[data-filter='category']", (event) => {
			this.filters.category = event.currentTarget.value;
			this.render();
		});
		this.container.on("change", "[data-filter='status']", (event) => {
			this.filters.status = event.currentTarget.value;
			this.render();
		});
		this.container.on("change", "[data-filter='sort']", (event) => {
			this.filters.sort = event.currentTarget.value;
			this.render();
		});
		this.container.on("input", "[data-filter='search']", (event) => {
			this.filters.search = event.currentTarget.value.trim().toLowerCase();
			this.render();
		});
	}

	refresh() {
		this.set_state(__("Loading category budgets..."));
		frappe.call({
			method: "personal_expense_tracker.api.get_category_budget_dashboard",
			args: {
				budget_period: this.filters.period || null,
			},
			callback: (response) => {
				this.data = response.message || {};
				this.filters.period = this.data.period?.name || this.filters.period;
				this.render();
			},
			error: () => {
				this.set_state(__("Could not load category budgets."));
			},
		});
	}

	render() {
		this.render_period();
		this.render_filters();
		this.render_summary();
		this.render_cards();
	}

	render_period() {
		const period = this.data.period || {};
		this.container.find(".pet-desk-budget-period").html(
			`<strong>${this.escape(period.label || "")}</strong><span>${this.escape(period.from_date || "")} - ${this.escape(period.to_date || "")}</span>`
		);
	}

	render_filters() {
		const periodOptions = (this.data.available_periods || []).map((period) => ({
			value: period.name,
			label: period.label,
		}));
		this.set_options("period", periodOptions, this.filters.period);

		const categories = (this.data.categories || [])
			.map((item) => ({ value: item.category, label: item.category_label || item.category }))
			.sort((a, b) => a.label.localeCompare(b.label));
		this.set_options(
			"category",
			[{ value: "", label: __("All Categories") }].concat(categories),
			this.filters.category
		);

		this.set_options(
			"status",
			this.data.status_options || [{ value: "", label: __("All Statuses") }],
			this.filters.status
		);
		this.container.find("[data-filter='sort']").val(this.filters.sort);
		this.container.find("[data-filter='search']").val(this.filters.search);
	}

	set_options(fieldname, options, selected) {
		this.container.find(`[data-filter='${fieldname}']`).html(
			options
				.map(
					(option) =>
						`<option value="${this.escape(option.value)}"${option.value === selected ? " selected" : ""}>${this.escape(option.label)}</option>`
				)
				.join("")
		);
	}

	render_summary() {
		const summary = this.data.summary || {};
		const highest = summary.highest_usage_category;
		const cards = [
			[__("Total income"), summary.total_income_display || "SYP 0.00", "green"],
			[__("Income used"), `${summary.income_usage_percent || 0}%`, "blue"],
			[__("Income left"), summary.income_remaining_display || "SYP 0.00", summary.income_remaining < 0 ? "red" : "green"],
			[__("Total allocated"), summary.total_allocated_display || "SYP 0.00", "blue"],
			[__("Budgeted spent"), summary.total_spent_display || "SYP 0.00", "pink"],
			[__("Total remaining"), summary.total_remaining_display || "SYP 0.00", summary.total_remaining < 0 ? "red" : "green"],
			[__("Unbudgeted Spending"), summary.total_unbudgeted_display || "SYP 0.00", "orange"],
			[__("Exceeded"), String(summary.exceeded_count || 0), "red"],
			[__("Highest usage"), highest ? `${highest.category_label} · ${highest.usage_percent}%` : __("No categories yet."), "purple"],
		];

		this.container.find(".pet-desk-budget-summary").html(
			cards
				.map(
					([label, value, accent]) => `
						<article class="pet-desk-budget-summary-card pet-accent-${accent}">
							<span>${this.escape(label)}</span>
							<strong>${this.escape(value)}</strong>
						</article>`
				)
				.join("")
		);
	}

	render_cards() {
		const rows = this.get_filtered_rows();
		if (!rows.length) {
			this.set_state(__("No category budgets match these filters."));
			this.container.find(".pet-desk-budget-grid").empty();
			return;
		}

		this.clear_state();
		this.container.find(".pet-desk-budget-grid").html(rows.map((row) => this.render_card(row)).join(""));
	}

	get_filtered_rows() {
		const search = this.filters.search;
		return (this.data.categories || [])
			.filter((row) => {
				if (this.filters.category && row.category !== this.filters.category) return false;
				if (this.filters.status && row.status !== this.filters.status) return false;
				if (!search) return true;
				return [row.category_label, row.category, row.status_label, row.insight]
					.join(" ")
					.toLowerCase()
					.includes(search);
			})
			.sort((a, b) => {
				switch (this.filters.sort) {
					case "remaining":
						return a.remaining - b.remaining;
					case "overrun":
						return b.overrun - a.overrun;
					case "category":
						return String(a.category_label).localeCompare(String(b.category_label));
					case "usage":
					default:
						return b.usage_percent - a.usage_percent;
				}
			});
	}

	render_card(row) {
		const statusClass = `pet-status-${row.status || "safe"}`;
		const budget = row.budget
			? row.budget_display
			: `${row.budget_source_label}${row.default_budget ? ` · ${row.default_budget_display}` : ""}`;
		return `
			<article class="pet-desk-budget-card ${statusClass}">
				<header>
					<div><span>${this.escape(row.period_label)}</span><h3>${this.escape(row.category_label)}</h3></div>
					<strong>${this.escape(row.status_label)}</strong>
				</header>
				<div class="pet-desk-budget-meter"><div style="width: ${Math.min(row.usage_width || 0, 100)}%"></div></div>
				<div class="pet-desk-budget-stats">
					<div><span>${__("Allocated")}</span><strong>${this.escape(budget)}</strong></div>
					<div><span>${__("Spent")}</span><strong>${this.escape(row.spent_display)}</strong></div>
					<div><span>${__("Remaining")}</span><strong>${this.escape(row.remaining_display)}</strong></div>
					<div><span>${__("Usage")}</span><strong>${this.escape(row.usage_percent)}%</strong></div>
				</div>
				<footer>
					<span>${this.escape(row.expense_count)} ${__("entries")}</span>
					<span>${__("Average")}: ${this.escape(row.average_expense_display)}</span>
					<span>${__("Last expense")}: ${this.escape(row.last_expense_date || "-")}</span>
					${row.overrun ? `<span>${__("Overrun")}: ${this.escape(row.overrun_display)}</span>` : ""}
				</footer>
				<p>${this.escape(row.insight || "")}</p>
			</article>`;
	}

	set_state(message) {
		this.container.find(".pet-desk-budget-state").removeClass("hide").text(message);
	}

	clear_state() {
		this.container.find(".pet-desk-budget-state").addClass("hide").empty();
	}

	escape(value) {
		return String(value || "")
			.replace(/&/g, "&amp;")
			.replace(/</g, "&lt;")
			.replace(/>/g, "&gt;")
			.replace(/\"/g, "&quot;")
			.replace(/'/g, "&#039;");
	}

	get_styles() {
		return `
			.pet-desk-budget-page { padding: 18px; }
			.pet-desk-budget-hero { display: flex; justify-content: space-between; gap: 18px; align-items: flex-end; padding: 20px; border: 1px solid var(--border-color); border-radius: 8px; background: var(--card-bg); margin-bottom: 16px; }
			.pet-desk-budget-hero p, .pet-desk-budget-hero span, .pet-desk-budget-filters span, .pet-desk-budget-card span, .pet-desk-budget-card footer { color: var(--text-muted); font-size: 12px; font-weight: 600; }
			.pet-desk-budget-hero h2 { margin: 4px 0 8px; font-size: 28px; }
			.pet-desk-budget-period { text-align: right; }
			.pet-desk-budget-period strong, .pet-desk-budget-period span { display: block; }
			.pet-desk-budget-summary { display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 12px; margin-bottom: 16px; }
			.pet-desk-budget-summary-card { padding: 16px; border: 1px solid var(--border-color); border-radius: 8px; background: var(--card-bg); }
			.pet-desk-budget-summary-card strong { display: block; margin-top: 8px; font-size: 18px; overflow-wrap: anywhere; }
			.pet-accent-blue { border-top: 3px solid var(--blue-500); } .pet-accent-pink { border-top: 3px solid var(--pink-500); } .pet-accent-green { border-top: 3px solid var(--green-500); } .pet-accent-orange { border-top: 3px solid var(--orange-500); } .pet-accent-red { border-top: 3px solid var(--red-500); } .pet-accent-purple { border-top: 3px solid var(--purple-500); }
			.pet-desk-budget-filters { display: grid; grid-template-columns: repeat(5, minmax(140px, 1fr)); gap: 12px; margin-bottom: 16px; }
			.pet-desk-budget-filters label { display: grid; gap: 6px; }
			.pet-desk-budget-filters select, .pet-desk-budget-filters input { min-height: 36px; border: 1px solid var(--border-color); border-radius: 6px; padding: 0 10px; background: var(--control-bg); color: var(--text-color); }
			.pet-desk-budget-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px; }
			.pet-desk-budget-card { padding: 16px; border: 1px solid var(--border-color); border-radius: 8px; background: var(--card-bg); }
			.pet-desk-budget-card header { display: flex; justify-content: space-between; gap: 16px; }
			.pet-desk-budget-card h3 { margin: 4px 0 0; font-size: 18px; }
			.pet-desk-budget-card header > strong { padding: 5px 9px; border-radius: 999px; background: var(--subtle-fg); font-size: 12px; white-space: nowrap; }
			.pet-status-safe header > strong { color: var(--green-600); } .pet-status-warning header > strong, .pet-status-danger header > strong { color: var(--orange-600); } .pet-status-exceeded header > strong { color: var(--red-600); } .pet-status-no_budget header > strong { color: var(--blue-600); }
			.pet-desk-budget-meter { height: 9px; margin: 14px 0; border-radius: 999px; background: var(--gray-200); overflow: hidden; }
			.pet-desk-budget-meter div { height: 100%; background: var(--green-500); } .pet-status-warning .pet-desk-budget-meter div, .pet-status-danger .pet-desk-budget-meter div { background: var(--orange-500); } .pet-status-exceeded .pet-desk-budget-meter div { background: var(--red-500); } .pet-status-no_budget .pet-desk-budget-meter div { background: var(--blue-500); }
			.pet-desk-budget-stats { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 8px; }
			.pet-desk-budget-stats div { padding: 10px; border-radius: 6px; background: var(--bg-color); }
			.pet-desk-budget-stats strong { display: block; margin-top: 5px; overflow-wrap: anywhere; }
			.pet-desk-budget-card footer { display: flex; flex-wrap: wrap; gap: 8px 16px; margin-top: 12px; }
			.pet-desk-budget-card p { margin: 10px 0 0; color: var(--text-muted); }
			.pet-desk-budget-state { padding: 22px; border: 1px dashed var(--border-color); border-radius: 8px; text-align: center; }
			@media (max-width: 1100px) { .pet-desk-budget-summary { grid-template-columns: repeat(3, minmax(0, 1fr)); } .pet-desk-budget-grid { grid-template-columns: 1fr; } }
			@media (max-width: 760px) { .pet-desk-budget-hero, .pet-desk-budget-summary, .pet-desk-budget-filters, .pet-desk-budget-stats { grid-template-columns: 1fr; display: grid; } .pet-desk-budget-period { text-align: left; } }
		`;
	}
}
