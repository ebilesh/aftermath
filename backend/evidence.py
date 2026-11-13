"""Read-only evidence extraction; never decides whether to credit an order."""
ALPHABET = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'
SYSTEM_PROGRAM = '11111111111111111111111111111111'


def validate_signature(signature):
    if not isinstance(signature, str) or not 64 <= len(signature) <= 88:
        raise ValueError('Enter a base58 signature encoding exactly 64 bytes.')
    value = 0
    for char in signature:
        if char not in ALPHABET:
            raise ValueError('Signature contains a non-base58 character.')
        value = value * 58 + ALPHABET.index(char)
    leading = len(signature) - len(signature.lstrip('1'))
    if leading + (value.bit_length() + 7) // 8 != 64:
        raise ValueError('A Solana transaction signature must decode to exactly 64 bytes.')


def summarize(result):
    if result is None:
        return {'status': 'not_found', 'transfers': [], 'warning': 'Not found at finalized commitment. This does not prove failure.'}
    if not isinstance(result, dict) or type(result.get('slot')) is not int:
        raise ValueError('RPC returned malformed transaction evidence.')
    meta = result.get('meta')
    status = 'unknown' if not isinstance(meta, dict) or 'err' not in meta else 'succeeded' if meta['err'] is None else 'failed'
    transfers = []
    message = (result.get('transaction') or {}).get('message') or {}
    groups = [('outer', message.get('instructions') or [])]
    for group in (meta or {}).get('innerInstructions') or []:
        groups.append((f'inner:{group.get("index")}', group.get('instructions') or []))
    for scope, instructions in groups:
        for index, instruction in enumerate(instructions):
            parsed = instruction.get('parsed') or {}
            if instruction.get('programId') != SYSTEM_PROGRAM or parsed.get('type') not in ('transfer', 'transferWithSeed'):
                continue
            info = parsed.get('info') or {}
            amount = info.get('lamports')
            if type(amount) is not int or amount < 0 or not isinstance(info.get('source'), str) or not isinstance(info.get('destination'), str):
                continue
            transfers.append({'scope': scope, 'instruction': index, 'source': info['source'], 'destination': info['destination'], 'lamports': str(amount), 'applied': status == 'succeeded'})
    return {'status': status, 'transfers': transfers, 'warning': 'Parsed native SOL instructions only. Failed or unknown execution is not payment evidence. SPL tokens, balance changes, and merchant intent are not validated.'}
