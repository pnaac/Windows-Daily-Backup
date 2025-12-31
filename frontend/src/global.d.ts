/// <reference types="svelte" />
/// <reference types="vite/client" />

declare namespace svelteHTML {
  // Enhances Svelte's HTML attributes for IDE support
  // This helps when using custom actions or Svelte 5 specific attributes
  import type { HTMLAttributes } from 'svelte/elements';
  
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  type HTMLAttributes<T> = import('svelte/elements').HTMLAttributes<T>;
}

declare module '*.svelte' {
	import { SvelteComponent } from 'svelte';
	const component: typeof SvelteComponent;
	export default component;
}
