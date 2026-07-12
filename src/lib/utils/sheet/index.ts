import { cubicOut } from 'svelte/easing';
import type { TransitionConfig } from 'svelte/transition';

// Mobile bottom-sheet behaviors shared by Dropdown menus and Modals:
// native-feeling drag-to-dismiss plus a slide-up entrance transition.
// Everything no-ops on desktop widths so only phones get the sheet feel.

const MOBILE_QUERY = '(max-width: 768px)';

export const isMobileSheet = () =>
	typeof window !== 'undefined' && window.matchMedia(MOBILE_QUERY).matches;

type SheetDragParams = {
	onDismiss: () => void;
};

// Svelte action: grab a bottom sheet and pull it down to dismiss, with
// spring-back below the threshold. Uses the standalone `translate`
// property so it composes with (and isn't blocked by) the `transform`
// overrides in custom.css.
export function sheetDrag(node: HTMLElement, params: SheetDragParams) {
	let opts = params;
	let startY = 0;
	let lastY = 0;
	let lastT = 0;
	let dy = 0;
	let velocity = 0;
	let dragging = false;

	const onTouchStart = (e: TouchEvent) => {
		if (!isMobileSheet() || e.touches.length !== 1) return;
		startY = lastY = e.touches[0].clientY;
		lastT = performance.now();
		dy = 0;
		velocity = 0;
		dragging = false;
		node.style.transition = '';
	};

	const onTouchMove = (e: TouchEvent) => {
		if (!isMobileSheet() || e.touches.length !== 1) return;
		const y = e.touches[0].clientY;
		const delta = y - startY;
		const now = performance.now();
		velocity = (y - lastY) / Math.max(1, now - lastT);
		lastY = y;
		lastT = now;

		// Only take over a downward pull while the sheet isn't scrolled,
		// so inner scrolling keeps working normally.
		if (!dragging) {
			if (delta > 8 && node.scrollTop <= 0) {
				dragging = true;
			} else {
				return;
			}
		}
		dy = Math.max(0, delta);
		if (e.cancelable) {
			e.preventDefault();
		}
		node.style.translate = `0 ${dy}px`;
	};

	const onTouchEnd = () => {
		if (!dragging) return;
		dragging = false;
		const dismiss = dy > Math.min(140, node.offsetHeight * 0.3) || (velocity > 0.55 && dy > 24);
		if (dismiss) {
			node.style.transition = 'translate 200ms cubic-bezier(0.4, 0, 1, 1), opacity 200ms linear';
			node.style.translate = '0 110%';
			node.style.opacity = '0.5';
			setTimeout(() => opts.onDismiss?.(), 190);
		} else {
			node.style.transition = 'translate 220ms cubic-bezier(0.32, 0.72, 0.33, 1)';
			node.style.translate = '0 0';
			setTimeout(() => {
				node.style.transition = '';
			}, 240);
		}
		dy = 0;
	};

	node.addEventListener('touchstart', onTouchStart, { passive: true });
	node.addEventListener('touchmove', onTouchMove, { passive: false });
	node.addEventListener('touchend', onTouchEnd);
	node.addEventListener('touchcancel', onTouchEnd);

	return {
		update(next: SheetDragParams) {
			opts = next;
		},
		destroy() {
			node.removeEventListener('touchstart', onTouchStart);
			node.removeEventListener('touchmove', onTouchMove);
			node.removeEventListener('touchend', onTouchEnd);
			node.removeEventListener('touchcancel', onTouchEnd);
		}
	};
}

// iOS-style sheet entrance/exit for Svelte transition: directives.
export const sheetSlide = (node: Element, { duration = 240 } = {}): TransitionConfig => ({
	duration,
	easing: cubicOut,
	css: (t) => `translate: 0 ${(1 - t) * 28}px; opacity: ${0.4 + t * 0.6};`
});
