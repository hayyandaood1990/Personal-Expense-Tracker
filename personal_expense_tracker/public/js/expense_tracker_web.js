(() => {
	const dataElement = document.getElementById("pet-dashboard-data");
	if (!dataElement) return;

	const data = JSON.parse(dataElement.textContent || "{}");
	const translations = data.translations || {};
	const palette = ["#62a8ff", "#ff6f9f", "#4fd18b", "#f5b84b", "#5eead4", "#c084fc", "#f97316"];

	startFlowField();
	drawMonthlyChart(data.monthly || {});
	drawCategoryChart(data.categories || []);
	renderCategoryLegend(data.categories || []);
	renderCurrencyBars(data.currencies || []);

	function startFlowField() {
		const canvas = document.getElementById("pet-flow-field");
		if (!canvas) return;

		const ctx = canvas.getContext("2d");
		const particles = [];
		let width = 0;
		let height = 0;
		let animationFrame = null;

		function resize() {
			width = canvas.width = window.innerWidth * window.devicePixelRatio;
			height = canvas.height = window.innerHeight * window.devicePixelRatio;
			canvas.style.width = `${window.innerWidth}px`;
			canvas.style.height = `${window.innerHeight}px`;
			particles.length = 0;

			const count = Math.min(90, Math.max(34, Math.floor(window.innerWidth / 18)));
			for (let i = 0; i < count; i += 1) {
				particles.push({
					x: Math.random() * width,
					y: Math.random() * height,
					vx: (Math.random() - 0.5) * 0.42 * window.devicePixelRatio,
					vy: (Math.random() - 0.5) * 0.42 * window.devicePixelRatio,
					r: (Math.random() * 1.9 + 0.7) * window.devicePixelRatio,
					color: palette[i % palette.length],
				});
			}
		}

		function tick() {
			ctx.clearRect(0, 0, width, height);
			ctx.globalCompositeOperation = "lighter";

			for (let i = 0; i < particles.length; i += 1) {
				const particle = particles[i];
				particle.x += particle.vx;
				particle.y += particle.vy;

				if (particle.x < 0 || particle.x > width) particle.vx *= -1;
				if (particle.y < 0 || particle.y > height) particle.vy *= -1;

				ctx.beginPath();
				ctx.fillStyle = particle.color;
				ctx.globalAlpha = 0.6;
				ctx.arc(particle.x, particle.y, particle.r, 0, Math.PI * 2);
				ctx.fill();

				for (let j = i + 1; j < particles.length; j += 1) {
					const other = particles[j];
					const dx = particle.x - other.x;
					const dy = particle.y - other.y;
					const distance = Math.sqrt(dx * dx + dy * dy);
					const limit = 132 * window.devicePixelRatio;
					if (distance < limit) {
						ctx.beginPath();
						ctx.strokeStyle = particle.color;
						ctx.globalAlpha = (1 - distance / limit) * 0.16;
						ctx.lineWidth = window.devicePixelRatio;
						ctx.moveTo(particle.x, particle.y);
						ctx.lineTo(other.x, other.y);
						ctx.stroke();
					}
				}
			}

			ctx.globalAlpha = 1;
			ctx.globalCompositeOperation = "source-over";
			animationFrame = window.requestAnimationFrame(tick);
		}

		window.addEventListener("resize", resize);
		resize();
		if (animationFrame) window.cancelAnimationFrame(animationFrame);
		tick();
	}

	function drawMonthlyChart(monthly) {
		const canvas = document.getElementById("pet-monthly-chart");
		if (!canvas) return;

		const values = monthly.values || [];
		const labels = monthly.labels || [];
		const ctx = setupCanvas(canvas);
		const { width, height } = canvas;
		const pad = 42 * window.devicePixelRatio;
		const chartWidth = width - pad * 2;
		const chartHeight = height - pad * 1.7;
		const max = Math.max(...values, 1);

		ctx.clearRect(0, 0, width, height);
		ctx.lineWidth = window.devicePixelRatio;
		ctx.strokeStyle = "rgba(255,255,255,0.09)";
		ctx.fillStyle = "rgba(255,255,255,0.5)";
		ctx.font = `${12 * window.devicePixelRatio}px sans-serif`;

		for (let i = 0; i <= 4; i += 1) {
			const y = pad + chartHeight * (i / 4);
			ctx.beginPath();
			ctx.moveTo(pad, y);
			ctx.lineTo(width - pad, y);
			ctx.stroke();
		}

		const points = values.map((value, index) => {
			const x = pad + (chartWidth / Math.max(values.length - 1, 1)) * index;
			const y = pad + chartHeight - (value / max) * chartHeight;
			return { x, y, value, label: labels[index] };
		});

		ctx.beginPath();
		points.forEach((point, index) => {
			if (index === 0) ctx.moveTo(point.x, point.y);
			else ctx.lineTo(point.x, point.y);
		});
		ctx.strokeStyle = "#62a8ff";
		ctx.lineWidth = 3 * window.devicePixelRatio;
		ctx.stroke();

		points.forEach((point, index) => {
			ctx.beginPath();
			ctx.fillStyle = valueColor(index);
			ctx.arc(point.x, point.y, 4.5 * window.devicePixelRatio, 0, Math.PI * 2);
			ctx.fill();

			if (index % 2 === 0) {
				ctx.fillStyle = "rgba(255,255,255,0.62)";
				ctx.fillText(String(point.label || "").slice(0, 3), point.x - 10, height - 18);
			}
		});
	}

	function drawCategoryChart(categories) {
		const canvas = document.getElementById("pet-category-chart");
		if (!canvas) return;

		const ctx = setupCanvas(canvas);
		const { width, height } = canvas;
		const total = categories.reduce((sum, item) => sum + item.value, 0);
		const radius = Math.min(width, height) * 0.34;
		const centerX = width / 2;
		const centerY = height / 2;
		let angle = -Math.PI / 2;

		ctx.clearRect(0, 0, width, height);

		if (!total) {
			ctx.strokeStyle = "rgba(255,255,255,0.16)";
			ctx.lineWidth = 24 * window.devicePixelRatio;
			ctx.beginPath();
			ctx.arc(centerX, centerY, radius, 0, Math.PI * 2);
			ctx.stroke();
			return;
		}

		categories.forEach((item, index) => {
			const slice = (item.value / total) * Math.PI * 2;
			ctx.beginPath();
			ctx.strokeStyle = valueColor(index);
			ctx.lineWidth = 28 * window.devicePixelRatio;
			ctx.arc(centerX, centerY, radius, angle, angle + slice);
			ctx.stroke();
			angle += slice;
		});

		ctx.fillStyle = "rgba(255,255,255,0.86)";
		ctx.font = `${16 * window.devicePixelRatio}px sans-serif`;
		ctx.textAlign = "center";
		ctx.fillText("SYP", centerX, centerY - 2 * window.devicePixelRatio);
		ctx.fillText(formatCompact(total), centerX, centerY + 20 * window.devicePixelRatio);
		ctx.textAlign = "left";
	}

	function renderCategoryLegend(categories) {
		const container = document.getElementById("pet-category-list");
		if (!container) return;

		if (!categories.length) {
			container.innerHTML = `<div class="pet-empty-state">${escapeHtml(
				translate("no_categories_yet", "No categories yet.")
			)}</div>`;
			return;
		}

		container.innerHTML = categories
			.slice(0, 6)
			.map(
				(item, index) => `
				<div class="pet-legend-row">
					<span class="pet-swatch" style="--color: ${valueColor(index)}"></span>
					<strong>${escapeHtml(item.label)}</strong>
					<span>${escapeHtml(item.display)}</span>
				</div>
			`
			)
			.join("");
	}

	function renderCurrencyBars(currencies) {
		const container = document.getElementById("pet-currency-bars");
		if (!container) return;

		if (!currencies.length) {
			container.innerHTML = `<div class="pet-empty-state">${escapeHtml(
				translate("no_currency_exposure_yet", "No currency exposure yet.")
			)}</div>`;
			return;
		}

		const max = Math.max(...currencies.map((item) => item.base), 1);
		container.innerHTML = currencies
			.map((item, index) => {
				const width = Math.max(3, (item.base / max) * 100);
				return `
					<div class="pet-bar-row" style="--accent: ${valueColor(index)}">
						<div class="pet-panel-header">
							<strong>${escapeHtml(item.currency)}</strong>
							<span>${escapeHtml(item.base_display)}</span>
						</div>
						<div class="pet-bar-track"><div style="width: ${width}%"></div></div>
						<span>${item.count} ${escapeHtml(translate("entries", "entries"))}</span>
					</div>
				`;
			})
			.join("");
	}

	function setupCanvas(canvas) {
		const rect = canvas.getBoundingClientRect();
		const ratio = window.devicePixelRatio || 1;
		canvas.width = rect.width * ratio;
		canvas.height = rect.height * ratio;
		return canvas.getContext("2d");
	}

	function valueColor(index) {
		return palette[index % palette.length];
	}

	function formatCompact(value) {
		if (value >= 1000000) return `${(value / 1000000).toFixed(1)}M`;
		if (value >= 1000) return `${Math.round(value / 1000)}K`;
		return String(Math.round(value));
	}

	function translate(key, fallback) {
		return translations[key] || fallback;
	}

	function escapeHtml(value) {
		return String(value || "")
			.replace(/&/g, "&amp;")
			.replace(/</g, "&lt;")
			.replace(/>/g, "&gt;")
			.replace(/"/g, "&quot;")
			.replace(/'/g, "&#039;");
	}
})();
