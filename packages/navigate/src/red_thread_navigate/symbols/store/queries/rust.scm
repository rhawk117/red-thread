; Adapted from tree-sitter-rust TAGS_QUERY at version 0.24.2 (github.com/tree-sitter/tree-sitter-rust).
; Methods carry @parent, the impl's type, and trait impls carry @impl, the trait the impl implements.
; The MIT License (MIT)
;
; Copyright (c) 2017 Maxim Sokolov
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

(struct_item
  name: (type_identifier) @name) @definition.struct

(union_item
  name: (type_identifier) @name) @definition.struct

(enum_item
  name: (type_identifier) @name) @definition.enum

(type_item
  name: (type_identifier) @name) @definition.type

(trait_item
  name: (type_identifier) @name) @definition.trait

(mod_item
  name: (identifier) @name) @definition.module

(const_item
  name: (identifier) @name) @definition.constant

(static_item
  name: (identifier) @name) @definition.constant

(source_file
  (function_item
    name: (identifier) @name) @definition.function)

(mod_item
  body: (declaration_list
    (function_item
      name: (identifier) @name) @definition.function))

(trait_item
  body: (declaration_list
    [
      (function_item
        name: (identifier) @name) @definition.method
      (function_signature_item
        name: (identifier) @name) @definition.method
    ]))

(impl_item
  type: [
    (type_identifier) @parent
    (generic_type
      type: (type_identifier) @parent)
    (reference_type
      type: [
        (type_identifier) @parent
        (generic_type
          type: (type_identifier) @parent)
      ])
  ]
  !trait
  body: (declaration_list
    (function_item
      name: (identifier) @name) @definition.method))

(impl_item
  trait: (_) @impl
  type: [
    (type_identifier) @parent
    (generic_type
      type: (type_identifier) @parent)
    (reference_type
      type: [
        (type_identifier) @parent
        (generic_type
          type: (type_identifier) @parent)
      ])
  ]
  body: (declaration_list
    (function_item
      name: (identifier) @name) @definition.method))

(call_expression
  function: (identifier) @name) @reference.call

(call_expression
  function: (field_expression
    field: (field_identifier) @name)) @reference.call

(call_expression
  function: (scoped_identifier
    name: (identifier) @name)) @reference.call

(macro_invocation
  macro: (identifier) @name) @reference.call

(impl_item
  trait: [
    (type_identifier) @name
    (generic_type
      type: (type_identifier) @name)
    (scoped_type_identifier
      name: (type_identifier) @name)
  ]) @reference.implementation

(trait_bounds
  [
    (type_identifier) @name
    (generic_type
      type: (type_identifier) @name)
    (scoped_type_identifier
      name: (type_identifier) @name)
  ]) @reference.type

(dynamic_type
  trait: [
    (type_identifier) @name
    (generic_type
      type: (type_identifier) @name)
    (scoped_type_identifier
      name: (type_identifier) @name)
  ]) @reference.type

(abstract_type
  trait: [
    (type_identifier) @name
    (generic_type
      type: (type_identifier) @name)
    (scoped_type_identifier
      name: (type_identifier) @name)
  ]) @reference.type

; A type name in use position. Each branch names its parent and field, so the name a
; struct_item, enum_item, type_item, trait_item or type parameter declares never matches.
[
  (parameter
    type: (type_identifier) @name)
  (function_item
    return_type: (type_identifier) @name)
  (let_declaration
    type: (type_identifier) @name)
  (field_declaration
    type: (type_identifier) @name)
  (type_arguments
    (type_identifier) @name)
  (struct_expression
    name: (type_identifier) @name)
  (scoped_type_identifier
    name: (type_identifier) @name)
] @reference.type
