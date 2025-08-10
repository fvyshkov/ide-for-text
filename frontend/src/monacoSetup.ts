import loader from '@monaco-editor/loader';

// Force Monaco to load workers from local public assets instead of CDN
loader.config({ paths: { vs: '/monaco/vs' } });

export default loader;


