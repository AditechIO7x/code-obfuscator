const { test } = require('node:test');
const assert = require('node:assert/strict');
const { readFileSync } = require('node:fs');
const vm = require('node:vm');

const source = readFileSync('api/index.py', 'utf8');
const script = source.split('async def root():')[1].split('<script>')[1].split('</script>')[0];

function page(fetch, clipboard = { writeText: async () => {} }) {
    const elements = {};
    let focused;
    let selected;
    for (const id of ['code', 'language', 'level', 'antiHooking', 'obfuscateButton',
        'loading', 'result', 'error', 'originalSize', 'obfuscatedSize', 'sizeIncrease',
        'codeOutput', 'copyStatus']) {
        elements[id] = { value: '', textContent: '', style: {}, disabled: false,
            focus() { focused = id; } };
    }
    elements.code.value = 'print("hello")';
    elements.language.value = 'python';
    elements.level.value = '5';
    const context = vm.createContext({
        document: {
            getElementById: id => elements[id],
            createRange: () => ({ selectNodeContents: node => { selected = node; } }),
        },
        window: { getSelection: () => ({ removeAllRanges() {}, addRange() {} }) },
        navigator: { clipboard }, fetch,
    });
    vm.runInContext(script, context);
    return { context, elements, focused: () => focused, selected: () => selected };
}

const success = () => Promise.resolve({
    ok: true, json: async () => ({
        original_size: 14, obfuscated_size: 20, obfuscated_code: 'generated code',
    }),
});

test('invalid levels and blank source never submit and focus the invalid field', async () => {
    let calls = 0;
    const p = page(() => { calls++; return success(); });
    for (const value of ['', '0', '16', '2.5', 'NaN']) {
        p.elements.level.value = value;
        await p.context.obfuscateCode();
        assert.match(p.elements.error.textContent, /whole-number/);
        assert.equal(p.focused(), 'level');
    }
    p.elements.code.value = '   ';
    await p.context.obfuscateCode();
    assert.equal(p.focused(), 'code');
    assert.equal(calls, 0);
});

test('one request at a time; success restores controls and displays exact output', async () => {
    let finish;
    let calls = 0;
    const p = page(() => { calls++; return new Promise(resolve => { finish = resolve; }); });
    const pending = p.context.obfuscateCode();
    await p.context.obfuscateCode();
    assert.equal(calls, 1);
    assert.equal(p.elements.obfuscateButton.disabled, true);
    assert.equal(p.elements.loading.style.display, 'block');
    finish(await success());
    await pending;
    assert.equal(p.elements.obfuscateButton.disabled, false);
    assert.equal(p.elements.obfuscateButton.textContent, 'Obfuscate Code');
    assert.equal(p.elements.codeOutput.textContent, 'generated code');
    assert.equal(p.elements.result.style.display, 'block');
    assert.equal(p.elements.loading.style.display, 'none');
});

test('HTTP and network failures restore the button and preserve source for retry', async () => {
    for (const fetch of [async () => ({ ok: false }), async () => { throw new Error('Failed to fetch'); }]) {
        const p = page(fetch);
        await p.context.obfuscateCode();
        assert.equal(p.elements.obfuscateButton.disabled, false);
        assert.equal(p.elements.loading.style.display, 'none');
        assert.equal(p.elements.error.style.display, 'block');
        assert.match(p.elements.error.textContent, /try again/);
        assert.equal(p.elements.code.value, 'print("hello")');
    }
});

test('copy preserves exact output and confirms success', async () => {
    let copied;
    const p = page(success, { writeText: async text => { copied = text; } });
    p.elements.codeOutput.textContent = 'line one\n  line two';
    await p.context.copyOutput();
    assert.equal(copied, p.elements.codeOutput.textContent);
    assert.equal(p.elements.copyStatus.textContent, 'Code copied.');
});

test('denied or unavailable clipboard selects output for manual copying', async () => {
    for (const clipboard of [undefined, { writeText: async () => { throw new Error('denied'); } }]) {
        const p = page(success, clipboard);
        if (clipboard === undefined) vm.runInContext('navigator.clipboard = undefined', p.context);
        await p.context.copyOutput();
        assert.equal(p.focused(), 'codeOutput');
        assert.equal(p.selected(), p.elements.codeOutput);
        assert.match(p.elements.copyStatus.textContent, /output is selected/);
    }
});
