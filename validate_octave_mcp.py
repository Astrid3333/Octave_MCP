#!/usr/bin/env python3
"""Validador MCP Octave - 3 modos de validación"""
import json
import sys
import re
from collections import Counter

def validate_tools_json(filepath="octave_mcp_tools.json"):
    """Modo 1: Validar estructura del archivo de tools"""
    errors = []
    warnings = []
    
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        return {"status": "FAIL", "mode": "validate_tools_json", "errors": [f"JSON inválido: {e}"]}
    except FileNotFoundError:
        return {"status": "FAIL", "mode": "validate_tools_json", "errors": [f"Archivo no encontrado: {filepath}"]}
    
    if "tools" not in data:
        errors.append("Falta campo 'tools'")
    
    if "mcpName" not in data:
        errors.append("Falta campo 'mcpName'")
    
    tools = data.get("tools", [])
    if not tools:
        errors.append("Array 'tools' vacío")
    
    ids = [t.get("id") for t in tools]
    names = [t.get("name") for t in tools]
    categories = [t.get("category") for t in tools]
    
    dup_ids = [i for i, c in Counter(ids).items() if c > 1]
    if dup_ids:
        errors.append(f"IDs duplicados: {dup_ids}")
    
    dup_names = [n for n, c in Counter(names).items() if c > 1]
    if dup_names:
        errors.append(f"Nombres duplicados: {dup_names}")
    
    if None in ids or 0 in ids:
        errors.append("IDs faltantes o cero")
    
    expected = set(range(1, len(tools) + 1))
    actual = set(ids)
    missing = expected - actual
    if missing:
        warnings.append(f"IDs faltantes en secuencia: {sorted(missing)}")
    
    for t in tools:
        tid = t.get("id", "?")
        if "name" not in t:
            errors.append(f"Tool id={tid}: falta 'name'")
        if "category" not in t:
            errors.append(f"Tool id={tid}: falta 'category'")
        if "description" not in t:
            errors.append(f"Tool id={tid}: falta 'description'")
        elif len(t.get("description", "")) < 10:
            warnings.append(f"Tool id={tid} ({t.get('name')}): descripción muy corta")
    
    has_finish = any(t.get("name") == "finish" for t in tools)
    if not has_finish:
        warnings.append("No existe tool 'finish'")
    
    if "designPrinciples" not in data:
        warnings.append("Falta campo 'designPrinciples'")
    
    return {
        "status": "PASS" if not errors else "FAIL",
        "mode": "validate_tools_json",
        "total_tools": len(tools),
        "total_categories": len(set(categories)),
        "errors": errors,
        "warnings": warnings,
    }


def validate_mcp_config(filepath="octave_mcp_tools.json"):
    """Modo 2: Validar configuración contra protocolo MCP"""
    errors = []
    warnings = []
    
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        return {"status": "FAIL", "mode": "validate_mcp_config", "errors": [f"No se pudo leer: {e}"]}
    
    required_top = ["mcpName", "version", "description", "tools"]
    for field in required_top:
        if field not in data:
            errors.append(f"Campo requerido MCP ausente: '{field}'")
    
    version = data.get("version", "")
    if not re.match(r"^\d+\.\d+\.\d+$", str(version)):
        errors.append(f"Version inválida: '{version}' (esperado X.Y.Z)")
    
    tools = data.get("tools", [])
    for t in tools:
        tid = t.get("id", "?")
        if not isinstance(t.get("id"), int):
            errors.append(f"Tool id={tid}: 'id' debe ser entero")
        name = t.get("name", "")
        if not re.match(r"^[a-z][a-z0-9_]*$", str(name)):
            warnings.append(f"Tool id={tid}: nombre '{name}' no cumple snake_case")
        desc = t.get("description", "")
        if len(str(desc)) < 20:
            warnings.append(f"Tool id={tid} ({name}): descripción MCP debe ser >= 20 chars")
    
    categories = set(t.get("category", "") for t in tools)
    if "" in categories:
        errors.append("Tools sin categoría asignada")
    
    principles = data.get("designPrinciples", [])
    if len(principles) > 20:
        warnings.append(f"designPrinciples tiene {len(principles)} (máx recomendado: 20)")
    
    return {
        "status": "PASS" if not errors else "FAIL",
        "mode": "validate_mcp_config",
        "mcp_name": data.get("mcpName"),
        "version": version,
        "errors": errors,
        "warnings": warnings,
    }


def octave_validate(code):
    """Modo 3: Validar código Octave (sintaxis + semántica básica)"""
    errors = []
    warnings = []
    
    lines = code.split("\n")
    open_blocks = 0
    block_types = []
    
    block_starters = re.compile(r"^\s*(if|for|while|function|switch|try|parfor)\b")
    block_enders = re.compile(r"^\s*(end|endif|endfor|endwhile|endswitch|end_try_catch|endfunction)\b")
    
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        
        if stripped.startswith("%") or stripped.startswith("#"):
            continue
        
        code_part = re.split(r"%|#", line)[0] if not stripped.startswith(("'", '"')) else line
        
        if block_starters.search(code_part):
            open_blocks += 1
            match = block_starters.match(code_part)
            block_types.append((i, match.group(1)))
        
        if block_enders.search(code_part):
            open_blocks -= 1
            if block_types:
                block_types.pop()
            if open_blocks < 0:
                errors.append(f"Línea {i}: 'end' sin bloque de apertura")
                open_blocks = 0
        
        if re.search(r"[^=<>!]=[^=]", code_part) and re.search(r"[+\-*/^]", code_part):
            pass
        
        if re.search(r"\b\w+\s*\(", code_part):
            open_parens = code_part.count("(") - code_part.count(")")
            if open_parens > 0:
                warnings.append(f"Línea {i}: paréntesis sin cerrar ({open_parens} sin cerrar)")
    
    if open_blocks > 0:
        for ln, btype in block_types:
            errors.append(f"Línea {ln}: bloque '{btype}' sin 'end'")
    
    if not code.strip():
        errors.append("Código vacío")
    
    return {
        "status": "PASS" if not errors else "FAIL",
        "mode": "octave_validate",
        "lines": len(lines),
        "errors": errors,
        "warnings": warnings,
    }


def run_all(filepath="octave_mcp_tools.json", code=None):
    """Ejecutar los 3 modos de validación"""
    results = []
    
    r1 = validate_tools_json(filepath)
    results.append(r1)
    
    r2 = validate_mcp_config(filepath)
    results.append(r2)
    
    if code:
        r3 = octave_validate(code)
        results.append(r3)
    
    all_pass = all(r["status"] == "PASS" for r in results)
    
    return {
        "overall": "PASS" if all_pass else "FAIL",
        "checks": len(results),
        "results": results,
    }


if __name__ == "__main__":
    filepath = "octave_mcp_tools.json"
    code = None
    
    if len(sys.argv) > 1:
        code = sys.argv[1]
    elif not sys.stdin.isatty():
        code = sys.stdin.read()
    
    result = run_all(filepath, code)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    sys.exit(0 if result["overall"] == "PASS" else 1)
