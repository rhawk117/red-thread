; red-thread's own query for HCL as Terraform reads it (tree-sitter-hcl ships none).
; A definition or reference is addressed as Terraform writes it. @name is the first
; part of the address and each @tail is a further part, joined with dots; the backend
; maps the block keywords "variable" and "locals" to "var" and "local".

(block
  (identifier) @name
  (string_lit
    (template_literal) @tail)
  (body)
  (#eq? @name "module")) @definition.module

(block
  (identifier) @name
  (string_lit
    (template_literal) @tail)
  (body)
  (#eq? @name "variable")) @definition.variable

(block
  (identifier) @name
  (string_lit
    (template_literal) @tail)
  (body)
  (#eq? @name "output")) @definition.output

(block
  (identifier) @name
  (string_lit
    (template_literal) @tail)
  (string_lit
    (template_literal) @tail)
  (body)
  (#eq? @name "data")) @definition.data

(block
  (identifier) @keyword
  (string_lit
    (template_literal) @name)
  (string_lit
    (template_literal) @tail)
  (body)
  (#eq? @keyword "resource")) @definition.resource

(block
  (identifier) @name
  (body
    (attribute
      (identifier) @tail) @definition.local)
  (#eq? @name "locals"))

(expression
  (variable_expr
    (identifier) @name)
  .
  (get_attr
    (identifier) @tail)
  (#any-of? @name "var" "local" "module")) @reference.address

(expression
  (variable_expr
    (identifier) @name)
  .
  (get_attr
    (identifier) @tail)
  .
  (get_attr
    (identifier) @tail)
  (#eq? @name "data")) @reference.address

(expression
  (variable_expr
    (identifier) @name)
  .
  (get_attr
    (identifier) @tail)
  (#not-match? @name "^(var|local|module|data|each|count|path|self|terraform)$")) @reference.address
