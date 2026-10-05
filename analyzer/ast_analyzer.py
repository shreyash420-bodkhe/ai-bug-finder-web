from __future__ import annotations

import ast
import builtins
from typing import Any


class _BindingCollector(ast.NodeVisitor):
    def __init__(self) -> None:
        self.bindings: set[str] = set()

    def visit_Name(self, node: ast.Name) -> None:
        if isinstance(node.ctx, (ast.Store, ast.Del)):
            self.bindings.add(node.id)

    def visit_Import(self, node: ast.Import) -> None:
        self.bindings.update(alias.asname or alias.name.split(".")[0] for alias in node.names)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        self.bindings.update(alias.asname or alias.name for alias in node.names)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self.bindings.add(node.name)

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_Lambda(self, node: ast.Lambda) -> None:
        bindings = {
            argument.arg
            for argument in (
                *node.args.posonlyargs,
                *node.args.args,
                *node.args.kwonlyargs,
            )
        }
        if node.args.vararg:
            bindings.add(node.args.vararg.arg)
        if node.args.kwarg:
            bindings.add(node.args.kwarg.arg)
        self.scopes.append(bindings)
        self.visit(node.body)
        self.scopes.pop()

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self.bindings.add(node.name)


class _Visitor(ast.NodeVisitor):
    def __init__(self) -> None:
        self.issues: list[dict[str, Any]] = []
        self.scopes: list[set[str]] = [set()]

    @property
    def defined(self) -> set[str]:
        return self.scopes[-1]

    def _is_defined(self, name: str) -> bool:
        return name in set(dir(builtins)) or any(name in scope for scope in reversed(self.scopes))

    def _bind_target(self, target: ast.AST) -> None:
        for node in ast.walk(target):
            if isinstance(node, ast.Name):
                self.defined.add(node.id)

    def _function_bindings(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> set[str]:
        bindings = {
            argument.arg
            for argument in (
                *node.args.posonlyargs,
                *node.args.args,
                *node.args.kwonlyargs,
            )
        }
        if node.args.vararg:
            bindings.add(node.args.vararg.arg)
        if node.args.kwarg:
            bindings.add(node.args.kwarg.arg)
        for child in ast.walk(ast.Module(body=node.body, type_ignores=[])):
            if isinstance(child, ast.Name) and isinstance(child.ctx, (ast.Store, ast.Del)):
                bindings.add(child.id)
            elif isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and child is not node:
                bindings.add(child.name)
        return bindings

    def visit_Import(self, node: ast.Import) -> None:
        self.defined.update(alias.asname or alias.name.split(".")[0] for alias in node.names)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        self.defined.update(alias.asname or alias.name for alias in node.names)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self.defined.add(node.name)
        for decorator in node.decorator_list:
            self.visit(decorator)
        for default in (*node.args.defaults, *node.args.kw_defaults):
            if default:
                self.visit(default)
        if node.returns:
            self.visit(node.returns)
        self.scopes.append(self._function_bindings(node))
        for statement in node.body:
            self.visit(statement)
        self.scopes.pop()

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self.defined.add(node.name)
        for base in node.bases:
            self.visit(base)
        for keyword in node.keywords:
            self.visit(keyword.value)
        self.scopes.append(set())
        for statement in node.body:
            self.visit(statement)
        self.scopes.pop()

    def visit_Assign(self, node: ast.Assign) -> None:
        for target in node.targets:
            self._bind_target(target)
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        self._bind_target(node.target)
        self.generic_visit(node)

    def visit_AugAssign(self, node: ast.AugAssign) -> None:
        self._bind_target(node.target)
        self.generic_visit(node)

    def visit_For(self, node: ast.For) -> None:
        self.visit(node.iter)
        self._bind_target(node.target)
        for statement in node.body:
            self.visit(statement)
        for statement in node.orelse:
            self.visit(statement)

    visit_AsyncFor = visit_For

    def visit_With(self, node: ast.With) -> None:
        for item in node.items:
            self.visit(item.context_expr)
            if item.optional_vars:
                self._bind_target(item.optional_vars)
        for statement in node.body:
            self.visit(statement)

    visit_AsyncWith = visit_With

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        if node.type:
            self.visit(node.type)
        if node.name:
            self.defined.add(node.name)
        for statement in node.body:
            self.visit(statement)

    def _visit_comprehension(self, node: ast.ListComp | ast.SetComp | ast.GeneratorExp | ast.DictComp) -> None:
        self.scopes.append(set())
        for generator in node.generators:
            self.visit(generator.iter)
            self._bind_target(generator.target)
            for condition in generator.ifs:
                self.visit(condition)
        if isinstance(node, ast.DictComp):
            self.visit(node.key)
            self.visit(node.value)
        else:
            self.visit(node.elt)
        self.scopes.pop()

    visit_ListComp = _visit_comprehension
    visit_SetComp = _visit_comprehension
    visit_GeneratorExp = _visit_comprehension
    visit_DictComp = _visit_comprehension

    def visit_Name(self, node: ast.Name) -> None:
        if isinstance(node.ctx, ast.Load) and not self._is_defined(node.id):
            self.issues.append({
                "category": "NameError",
                "title": f"Possible undefined name: {node.id}",
                "message": f"'{node.id}' is read before a local definition or import.",
                "line": node.lineno,
                "column": node.col_offset + 1,
                "severity": "warning",
            })


def analyze_ast(source: str) -> list[dict[str, Any]]:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    visitor = _Visitor()
    visitor.defined.update({"__file__", "__name__", "__package__", "__doc__", "__path__"})
    collector = _BindingCollector()
    for statement in tree.body:
        collector.visit(statement)
    visitor.defined.update(collector.bindings)
    visitor.visit(tree)
    unique: dict[tuple[int, str], dict[str, Any]] = {}
    for issue in visitor.issues:
        unique[(issue["line"], issue["title"])] = issue
    return list(unique.values())
