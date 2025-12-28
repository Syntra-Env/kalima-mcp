import test from 'node:test';
import assert from 'node:assert/strict';

// Test the regex patterns used for command shortcuts
const bareNumberMatch = (str) => /^(\d{1,3})$/.exec(str);
const colonFormatMatch = (str) => /^(\d{1,3}):(\d{1,3})$/.exec(str);

function transformCommand(command) {
    let trimmed = command.trim();

    const bare = bareNumberMatch(trimmed);
    const colon = colonFormatMatch(trimmed);

    if (colon) {
        return `read ${colon[1]}:${colon[2]}`;
    } else if (bare) {
        const surahNum = parseInt(bare[1], 10);
        if (surahNum >= 1 && surahNum <= 114) {
            return `read chapter ${surahNum}`;
        }
    }

    return trimmed;
}

test('bare number "2" transforms to "read chapter 2"', () => {
    assert.equal(transformCommand('2'), 'read chapter 2');
});

test('bare number "114" transforms to "read chapter 114"', () => {
    assert.equal(transformCommand('114'), 'read chapter 114');
});

test('bare number "1" transforms to "read chapter 1"', () => {
    assert.equal(transformCommand('1'), 'read chapter 1');
});

test('colon format "2:255" transforms to "read 2:255"', () => {
    assert.equal(transformCommand('2:255'), 'read 2:255');
});

test('colon format "1:1" transforms to "read 1:1"', () => {
    assert.equal(transformCommand('1:1'), 'read 1:1');
});

test('colon format "114:6" transforms to "read 114:6"', () => {
    assert.equal(transformCommand('114:6'), 'read 114:6');
});

test('non-numeric command passes through unchanged', () => {
    assert.equal(transformCommand('help'), 'help');
});

test('read command passes through unchanged', () => {
    assert.equal(transformCommand('read chapter 2'), 'read chapter 2');
});

test('number 0 does not transform (invalid surah)', () => {
    assert.equal(transformCommand('0'), '0');
});

test('number 115 does not transform (invalid surah)', () => {
    assert.equal(transformCommand('115'), '115');
});

test('whitespace is trimmed', () => {
    assert.equal(transformCommand('  2  '), 'read chapter 2');
});
