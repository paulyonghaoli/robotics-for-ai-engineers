# 6.5 Launch, parameters, and the configuration surface

**Status:** Code verified · **Prereqs:** lessons 6.1, 6.4 · **Time:** ~2 h · **Verified:** 2026-08-03, Python 3.13

---

## A. Why this matters

The two failures in this lesson have the same shape as everything else in the module: the system starts, every node reports healthy, and something is quietly not happening.

A parameter file with the right values in it that configures nothing. A publisher and a subscriber that never connect because of one leading slash. Neither is a bug in any node's code, neither produces a log line, and both are found in seconds once you resolve names the way the middleware does — which is the skill this lesson is actually about.

## B. A parameter has five places to come from

Weakest first:

```
default            what the node declared in code
yaml:/**           a wildcard block in a parameter file
yaml:<fq name>     a block naming this node exactly
launch             set in the launch file
cli                set with --ros-args -p on the command line
```

Running the exercise's configuration:

```
node: /robot1/controller
ignored blocks: ['/controller']

  frame_id   = base_link    (default)
  ki         = 0.05         (yaml:/**)
  kp         = 3.0          (launch)
  lookahead  = 1.2          (yaml:/robot1/controller)
  max_speed  = 2.0          (cli)
```

Look at the `ignored blocks` line. The parameter file has a `/controller` block setting `max_speed: 1.5` and `kp: 2.4`. The node is launched into the `/robot1` namespace, so its fully qualified name is `/robot1/controller`, and **that block matches nothing**. Every value in it is discarded, silently, by design — the file is keyed by node name and a key that names no node is not an error.

## C. The afternoon this costs

`max_speed` reads 2.0, which came from a command-line override somebody added while debugging. Delete that flag and:

```
max_speed = 0.5 (default)
```

Not 1.5. **The default** — because the parameter file has never been read for this node and the CLI flag was hiding that fact. The value you configured is right there in the file, spelled correctly, with the right type, and it has never once been used.

The same holds for `kp`: the launch file sets 3.0, the YAML says 2.4, and with the launch override removed the node runs at 1.0. Two parameters where the file is decorative and nothing says so.

**This is why the diagnostic is `ros2 param get`, not reading the YAML.** The file tells you what somebody intended; only the running node knows what it got. And `ros2 param dump` on a live node is the fastest way to find the whole class of problem at once.

### One node, five sources, resolved

The exercise's controller node receives values for five parameters from four
different places, and the resolution — which the exercise makes you compute
and the runtime performs silently — lands like this:

| Parameter | Winning value | Came from |
|---|---|---|
| `frame_id` | `base_link` | code default (nothing overrode it) |
| `ki` | 0.05 | YAML wildcard `/**` |
| `lookahead` | 1.2 | YAML, node-specific `/robot1/controller` |
| `kp` | 3.0 | launch file |
| `max_speed` | 2.0 | command line |

Each row is the *most specific, latest* source winning: defaults lose to the
wildcard YAML, the wildcard loses to the node-specific block, YAML loses to
launch, and launch loses to the command line. Note also what the exercise's
resolver **ignored**: a whole YAML block addressed to `/controller` — the
right node name in the wrong namespace — discarded without a message, which
is the parameter system's version of QoS's silent no-match. When a parameter
"refuses to change", the question is never whether your value is correct but
whether the block it sits in *addresses the node that actually exists*, and
`ros2 param describe` tells you which source won.

The same run demonstrates section D's slash trap: the node publishes
`/robot1/cmd_vel` (relative name, namespaced) while its intended consumer
subscribes to `/cmd_vel` (absolute, immune to the namespace), and the two do
not connect. One leading slash, one dead robot, zero error messages.

## D. One leading slash

The other silent failure:

```
publisher  -> /robot1/cmd_vel
subscriber -> /cmd_vel
connected  -> False
```

The controller publishes `cmd_vel` — a relative name, resolved against its namespace. The base driver subscribes to `/cmd_vel` — absolute, so **the namespace does not participate at all**. Two different topics, both nodes healthy, robot stationary.

The three rules are worth memorizing because they are the whole naming system:

| written as | resolves to | |
|---|---|---|
| `cmd_vel` | `/robot1/cmd_vel` | relative — namespace applies |
| `/cmd_vel` | `/cmd_vel` | absolute — namespace ignored |
| `~/state` | `/robot1/controller/state` | private — node's own namespace |

And the fix is a remapping in the launch file, touching neither node. That is the argument against hard-coding an absolute topic name in a node: it works on one robot and cannot be used on two, because **the same node launched into two namespaces is supposed to publish two different topics.** Namespacing is the feature; an absolute name opts out of it.

## E. Practice

<code-exercise src="ros-l5-launch"></code-exercise>

## F. In production

- **Verify with `ros2 param get`, never by reading the YAML.** The file is intent; the node is fact.
- **Prefer `/**` for parameters that genuinely apply everywhere** and exact names for the rest — but know that an exact name is a coupling to the launch namespace, which is what breaks here.
- **Every topic name relative or remapped.** An absolute name in node code is a node you can run once.
- **Log the effective configuration at startup.** Ten lines of "here is what I am actually using" removes this entire class of problem, and almost nobody does it.
- **Keep the launch file thin.** Composition, namespaces and remappings belong there; algorithm parameters belong in a versioned YAML that ships with the package.
- **Validate parameters when you declare them** — ranges, enums, required-ness. A node that refuses to start on a nonsensical gain is better than one that drives with it.

## G. Experiment

Add a startup log line to one of your nodes that prints every declared parameter with its value and its source, then launch it three ways: bare, with the parameter file, and with a CLI override. The output is a precedence table you derived rather than memorized, and the line is worth keeping permanently — it converts a silent failure into something a reviewer can see in the logs.

## H. Failure modes

- **A parameter block keyed for the wrong fully qualified name.** Silent, and the values look right in the file forever.
- **A CLI override masking it.** Now the system works and stops working when someone tidies up the launch command.
- **An absolute topic name in node code.** Fine on one robot, unusable on two.
- **Reading the YAML to answer "what is the gain?"** The node is the only authority.
- **Configuration in three places.** Precedence is well defined and nobody remembers it, so the answer is always "check the running node".
- **No startup log of the effective configuration.** The cheapest fix in this lesson and the least common.

## I. Questions

<quiz-bank src="ros-l5-quiz"></quiz-bank>

## J. References

- ROS 2 documentation on parameters, and on launch — particularly the sections on parameter files and node name matching.
- The ROS 2 name-resolution design document, which is where the three rules in section D come from.
- `ros2 param get` / `dump` / `list`, and `ros2 node info` — the tools that answer what the YAML cannot.
- [Lesson 12.3](../12-data-infra/03-schema-evolution.md) — a configuration surface is a schema, and a silently-ignored key is the same class of failure as a silently-misread field.

## K. Graded work & portfolio extension

**Graded:** the exercise above.

**Portfolio:** take your capstone's tunable constants and write the parameter file and launch file that would configure them for two robots in two namespaces. Then answer in writing: which parameters should be `/**`, which should be per-robot, and which should not be parameters at all because no operator should be changing them at runtime. That last category is the one people forget, and it is where a configurable system becomes a system nobody can reason about.
