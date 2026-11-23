; Adapted from tree-sitter-go queries/tags.scm at tag v0.25.0 (github.com/tree-sitter/tree-sitter-go).
; Methods carry @parent, the receiver's type, which the backend uses in place of nesting.
; The MIT License (MIT)
;
; Copyright (c) 2014 Max Brunsfeld
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

(function_declaration
  name: (identifier) @name) @definition.function

(method_declaration
  receiver: (parameter_list
    (parameter_declaration
      type: [
        (type_identifier) @parent
        (generic_type
          type: (type_identifier) @parent)
        (pointer_type
          [
            (type_identifier) @parent
            (generic_type
              type: (type_identifier) @parent)
          ])
      ]))
  name: (field_identifier) @name) @definition.method

(method_elem
  name: (field_identifier) @name) @definition.method

(type_spec
  name: (type_identifier) @name
  type: (struct_type)) @definition.struct

(type_spec
  name: (type_identifier) @name
  type: (interface_type)) @definition.interface

(type_spec
  name: (type_identifier) @name
  type: [
    (type_identifier)
    (qualified_type)
    (generic_type)
    (pointer_type)
    (slice_type)
    (array_type)
    (implicit_length_array_type)
    (map_type)
    (channel_type)
    (function_type)
    (parenthesized_type)
  ]) @definition.type

(type_alias
  name: (type_identifier) @name) @definition.type

(const_spec
  name: (identifier) @name) @definition.constant

(call_expression
  function: [
    (identifier) @name
    (parenthesized_expression
      (identifier) @name)
    (selector_expression
      field: (field_identifier) @name)
    (parenthesized_expression
      (selector_expression
        field: (field_identifier) @name))
  ]) @reference.call
