const isScalarArray = (val) => Array.isArray(val) && !isTuple(val);
const isTuple = (val) => Array.isArray(val) && val.length === 2;
class ConditionBuilder {
  constructor(left, operator, right, compound) {
    this.left = left;
    this.operator = operator;
    this.right = right;
    this.compound = compound;
  }
  // Factory for simple conditions
  static simple(field, operator, value) {
    const instance = new ConditionBuilder(field, operator, value, false);
    return instance;
  }
  // Factory for logical conditions
  static compound(operator, left, right = null) {
    const instance = new ConditionBuilder(left, operator, right, true);
    return instance;
  }
  // Logical combinators (Python __and__, __or__, __invert__)
  and(other) {
    return ConditionBuilder.compound("AND", this, other);
  }
  or(other) {
    return ConditionBuilder.compound("OR", this, other);
  }
  not() {
    return ConditionBuilder.compound("NOT", this, null);
  }
  // Serialization for JSON.stringify()
  toJSON() {
    if (this.compound) {
      const self = this;
      return {
        is_compound: true,
        left: self.left.toJSON(),
        operator: self.operator,
        right: self.right ? self.right.toJSON() : null
      };
    } else {
      const self = this;
      return {
        is_compound: false,
        left: self.left,
        operator: self.operator,
        right: this.serializeValue(self.right)
      };
    }
  }
  serializeValue(value) {
    if (value === null) return null;
    if (isScalarArray(value)) return value;
    if (isTuple(value)) return value;
    return value;
  }
}
class Column {
  constructor(name) {
    this.name = name;
  }
  // Comparison operators (Python __eq__, __ne__, etc.)
  eq(value) {
    return value === null ? ConditionBuilder.simple(this.name, "IS NULL", null) : ConditionBuilder.simple(this.name, "=", value);
  }
  ne(value) {
    return value === null ? ConditionBuilder.simple(this.name, "IS NOT NULL", null) : ConditionBuilder.simple(this.name, "!=", value);
  }
  lt(value) {
    return ConditionBuilder.simple(this.name, "<", value);
  }
  lte(value) {
    return ConditionBuilder.simple(this.name, "<=", value);
  }
  gt(value) {
    return ConditionBuilder.simple(this.name, ">", value);
  }
  gte(value) {
    return ConditionBuilder.simple(this.name, ">=", value);
  }
  // List operators
  in(values) {
    return ConditionBuilder.simple(this.name, "IN", values);
  }
  notIn(values) {
    return ConditionBuilder.simple(this.name, "NOT IN", values);
  }
  // Pattern matching
  like(pattern) {
    return ConditionBuilder.simple(this.name, "LIKE", pattern);
  }
  notLike(pattern) {
    return ConditionBuilder.simple(this.name, "NOT LIKE", pattern);
  }
  ilike(pattern) {
    return ConditionBuilder.simple(this.name, "ILIKE", pattern);
  }
  notIlike(pattern) {
    return ConditionBuilder.simple(this.name, "NOT ILIKE", pattern);
  }
  // Null checks
  isNull() {
    return ConditionBuilder.simple(this.name, "IS NULL", null);
  }
  isNotNull() {
    return ConditionBuilder.simple(this.name, "IS NOT NULL", null);
  }
  // Range
  between(low, high) {
    if (low === null || high === null) {
      throw new Error("BETWEEN requires non-null bounds");
    }
    return ConditionBuilder.simple(this.name, "BETWEEN", [low, high]);
  }
  notBetween(low, high) {
    if (low === null || high === null) {
      throw new Error("NOT BETWEEN requires non-null bounds");
    }
    return ConditionBuilder.simple(this.name, "NOT BETWEEN", [low, high]);
  }
  // Sorting
  asc() {
    return { column: this.name, direction: "ASC" };
  }
  desc() {
    return { column: this.name, direction: "DESC" };
  }
}
class TranscriptColumns {
  // Predefined transcript fields (matching Python columns.py)
  transcript_id = new Column("transcript_id");
  source_type = new Column("source_type");
  source_id = new Column("source_id");
  source_uri = new Column("source_uri");
  date = new Column("date");
  task_set = new Column("task_set");
  task_id = new Column("task_id");
  task_repeat = new Column("task_repeat");
  agent = new Column("agent");
  agent_args = new Column("agent_args");
  model = new Column("model");
  model_options = new Column("model_options");
  score = new Column("score");
  success = new Column("success");
  total_time = new Column("total_time");
  message_count = new Column("message_count");
  error = new Column("error");
  limit = new Column("limit");
  // Dynamic field access via Proxy
  static createProxy() {
    const instance = new TranscriptColumns();
    return new Proxy(instance, {
      get(target, prop) {
        if (typeof prop === "symbol") return void 0;
        if (prop.startsWith("_")) return void 0;
        if (prop in target) {
          return Reflect.get(target, prop);
        }
        return new Column(prop);
      }
    });
  }
  // Singleton instance
  static _instance = null;
  static get instance() {
    if (!TranscriptColumns._instance) {
      TranscriptColumns._instance = TranscriptColumns.createProxy();
    }
    return TranscriptColumns._instance;
  }
  // Bracket notation for JSON paths in transcript metadata
  field(name) {
    return new Column(name);
  }
}
TranscriptColumns.instance;
export {
  Column as C,
  ConditionBuilder as a
};
//# sourceMappingURL=transcriptColumns.js.map
