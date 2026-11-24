; Adapted from tree-sitter-typescript queries/tags.scm at tag v0.23.2 (github.com/tree-sitter/tree-sitter-typescript),
; which extends the JavaScript tags query, and from the vendored javascript.scm.
; The MIT License (MIT)
;
; Copyright (c) 2017 Max Brunsfeld
;
; Permission is hereby granted, free of charge, to any person obtaining a copy
; of this software and associated documentation files (the "Software"), to deal
; in the Software without restriction, including without limitation the rights
; to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
; copies of the Software, and to permit persons to whom the Software is
; furnished to do so, subject to the following conditions:
;
; The above copyright notice and this permission notice shall be included in all
; copies or substantial portions of the Software.
;
; THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
; IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
; FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
; AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
; LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
; OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
; SOFTWARE.

(method_definition
  name: (property_identifier) @name
  (#not-eq? @name "constructor")) @definition.method

[
  (class
    name: (_) @name)
  (class_declaration
    name: (_) @name)
] @definition.class

[
  (function_expression
    name: (identifier) @name)
  (function_declaration
    name: (identifier) @name)
  (generator_function
    name: (identifier) @name)
  (generator_function_declaration
    name: (identifier) @name)
] @definition.function

(assignment_expression
  left: [
    (identifier) @name
    (member_expression
      property: (property_identifier) @name)
  ]
  right: [(arrow_function) (function_expression)]) @definition.function

(pair
  key: (property_identifier) @name
  value: [(arrow_function) (function_expression) (generator_function)]) @definition.function

(variable_declarator
  name: (identifier) @name
  value: [(arrow_function) (function_expression) (generator_function)]) @definition.function

(call_expression
  function: (identifier) @name
  (#not-match? @name "^(require)$")) @reference.call

(call_expression
  function: (member_expression
    property: (property_identifier) @name)) @reference.call

(new_expression
  constructor: (_) @name) @reference.class

(function_signature
  name: (identifier) @name) @definition.function

(method_signature
  name: (property_identifier) @name) @definition.method

(abstract_method_signature
  name: (property_identifier) @name) @definition.method

(abstract_class_declaration
  name: (type_identifier) @name) @definition.class

(module
  name: (identifier) @name) @definition.module

(interface_declaration
  name: (type_identifier) @name) @definition.interface

(type_alias_declaration
  name: (type_identifier) @name) @definition.type

(enum_declaration
  name: (identifier) @name) @definition.enum

(type_annotation
  (type_identifier) @name) @reference.type

; A top-level declarator matches whatever its value is. For a function value two patterns match the
; same node, and the backend keeps the first match tree-sitter reports. That is the function pattern
; here, ahead of the constant patterns, because the constant patterns also name a value: with the
; same shape, the lower pattern index is reported first.
(program
  [
    (lexical_declaration
      (variable_declarator
      name: (identifier) @name
      value: [(arrow_function) (function_expression) (generator_function)]) @definition.function)
    (variable_declaration
      (variable_declarator
      name: (identifier) @name
      value: [(arrow_function) (function_expression) (generator_function)]) @definition.function)
  ])

(export_statement
  declaration: [
    (lexical_declaration
      (variable_declarator
      name: (identifier) @name
      value: [(arrow_function) (function_expression) (generator_function)]) @definition.function)
    (variable_declaration
      (variable_declarator
      name: (identifier) @name
      value: [(arrow_function) (function_expression) (generator_function)]) @definition.function)
  ])

(program
  (lexical_declaration
    kind: "const"
    [
      (variable_declarator
        name: (identifier) @name
        value: (_)) @definition.constant
      (variable_declarator
        name: (identifier) @name
        !value) @definition.constant
    ]))

(program
  (lexical_declaration
    kind: "let"
    [
      (variable_declarator
        name: (identifier) @name
        value: (_)) @definition.variable
      (variable_declarator
        name: (identifier) @name
        !value) @definition.variable
    ]))

(program
  (variable_declaration
    [
      (variable_declarator
        name: (identifier) @name
        value: (_)) @definition.variable
      (variable_declarator
        name: (identifier) @name
        !value) @definition.variable
    ]))

(export_statement
  declaration: (lexical_declaration
    kind: "const"
    [
      (variable_declarator
        name: (identifier) @name
        value: (_)) @definition.constant
      (variable_declarator
        name: (identifier) @name
        !value) @definition.constant
    ]))

(export_statement
  declaration: (lexical_declaration
    kind: "let"
    [
      (variable_declarator
        name: (identifier) @name
        value: (_)) @definition.variable
      (variable_declarator
        name: (identifier) @name
        !value) @definition.variable
    ]))

(export_statement
  declaration: (variable_declaration
    [
      (variable_declarator
        name: (identifier) @name
        value: (_)) @definition.variable
      (variable_declarator
        name: (identifier) @name
        !value) @definition.variable
    ]))
