# adw_response_dialog.py
#
# Copyright 2023 James Westman <james@jwestman.net>
#
# This file is free software; you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as
# published by the Free Software Foundation; either version 3 of the
# License, or (at your option) any later version.
#
# This file is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# SPDX-License-Identifier: LGPL-3.0-or-later


from ..decompiler import decompile_translatable, truthy
from .common import *
from .gobject_object import ObjectContent, validate_parent_type
from .values import StringValue


class ExtAdwResponseDialogFlag(AstNode):
    grammar = AnyOf(
        UseExact("flag", "destructive"),
        UseExact("flag", "suggested"),
        UseExact("flag", "disabled"),
    )

    @property
    def flag(self) -> str:
        return self.tokens["flag"]

    @validate()
    def unique(self):
        self.validate_unique_in_parent(
            f"Duplicate '{self.flag}' flag", check=lambda child: child.flag == self.flag
        )

    @validate()
    def exclusive(self):
        if self.flag in ["destructive", "suggested"]:
            self.validate_unique_in_parent(
                "'suggested' and 'destructive' are exclusive",
                check=lambda child: child.flag in ["destructive", "suggested"],
            )


class ExtAdwResponseDialogResponse(AstNode):
    grammar = [
        UseIdent("id"),
        Match(":").expected(),
        to_parse_node(StringValue).expected("a string or translatable string"),
        ZeroOrMore(ExtAdwResponseDialogFlag),
    ]

    @property
    def id(self) -> str:
        return self.tokens["id"]

    @property
    def flags(self) -> T.List[ExtAdwResponseDialogFlag]:
        return self.children[ExtAdwResponseDialogFlag]

    @property
    def appearance(self) -> T.Optional[str]:
        if any(flag.flag == "destructive" for flag in self.flags):
            return "destructive"
        elif any(flag.flag == "suggested" for flag in self.flags):
            return "suggested"
        else:
            return None

    @property
    def enabled(self) -> bool:
        return not any(flag.flag == "disabled" for flag in self.flags)

    @property
    def value(self) -> StringValue:
        return self.children[0]

    @property
    def document_symbol(self) -> DocumentSymbol:
        return DocumentSymbol(
            self.id,
            SymbolKind.Field,
            self.range,
            self.group.tokens["id"].range,
            self.value.range.text,
        )

    @validate("id")
    def unique_in_parent(self):
        self.validate_unique_in_parent(
            f"Duplicate response ID '{self.id}'",
            check=lambda child: child.id == self.id,
        )


class ExtAdwResponseDialog(AstNode):
    grammar = [
        Keyword("responses"),
        Match("[").expected(),
        Delimited(ExtAdwResponseDialogResponse, ","),
        "]",
    ]

    @property
    def responses(self) -> T.List[ExtAdwResponseDialogResponse]:
        return self.children

    @property
    def document_symbol(self) -> DocumentSymbol:
        return DocumentSymbol(
            "responses",
            SymbolKind.Array,
            self.range,
            self.group.tokens["responses"].range,
        )

    @validate("responses")
    def container_is_message_dialog_or_alert_dialog(self):
        try:
            validate_parent_type(self, "Adw", "MessageDialog", "responses")
        except:
            validate_parent_type(self, "Adw", "AlertDialog", "responses")

    @validate("responses")
    def unique_in_parent(self):
        self.validate_unique_in_parent("Duplicate responses block")

    @docs()
    def ref_docs(self):
        return get_docs_section("Syntax ExtAdwMessageDialog")


@completer(
    applies_in=[ObjectContent],
    applies_in_subclass=("Adw", "MessageDialog"),
    matches=new_statement_patterns,
)
def complete_adw_message_dialog(lsp, ast_node, match_variables):
    yield Completion(
        "responses", CompletionItemKind.Keyword, snippet="responses [\n\t$0\n]"
    )


@completer(
    applies_in=[ObjectContent],
    applies_in_subclass=("Adw", "AlertDialog"),
    matches=new_statement_patterns,
)
def complete_adw_alert_dialog(lsp, ast_node, match_variables):
    yield Completion(
        "responses", CompletionItemKind.Keyword, snippet="responses [\n\t$0\n]"
    )


@decompiler("responses")
def decompile_responses(ctx, gir):
    ctx.print(f"responses [")


@decompiler("response", cdata=True)
def decompile_response(
    ctx,
    gir,
    cdata,
    id,
    appearance=None,
    enabled=None,
    translatable=None,
    context=None,
    comments=None,
):
    comments, translated = decompile_translatable(
        cdata, translatable, context, comments
    )
    if comments is not None:
        ctx.print(comments)

    flags = ""
    if appearance is not None:
        flags += f" {appearance}"
    if enabled is not None and not truthy(enabled):
        flags += " disabled"

    ctx.print(f"{id}: {translated}{flags},")
