# SRE Road

- [SRE Road](#sre-road)
  - [What's SRE](#whats-sre)
  - [SRE and DevOps Shared practices](#sre-and-devops-shared-practices)
  - [SRE Key principle](#sre-key-principle)
  - [SRE's Mission](#sres-mission)
  - [SLA \& SLO \& SLI](#sla--slo--sli)
  - [The Four Golden Signals](#the-four-golden-signals)
  - [SRE Budgets](#sre-budgets)
  - [SRE Role Expectation](#sre-role-expectation)
  - [Observability](#observability)
    - [Metrics](#metrics)
      - [CPU Throttling](#cpu-throttling)
    - [Logs](#logs)
    - [Trace](#trace)
  - [What should be monitored](#what-should-be-monitored)
  - [Alert \& Incident Response](#alert--incident-response)
  - [SREcon22](#srecon22)
    - [SREcon22 APAC - Move Fast and Learn Things: Principles of Cognition, Teaming, and Coordination](#srecon22-apac---move-fast-and-learn-things-principles-of-cognition-teaming-and-coordination)
  - [Resource](#resource)

## What's SRE

`Site Reliability Engineering` is an engineering discipline devoted to helping an organization achieve the appropriate level of reliability in their systems, services, and products.

## SRE and DevOps Shared practices

- Automation
- Monitoring, Observability, Measure

## SRE Key principle

- Build feedback loop that help continuously get better.
- health check indicators (SLI, SLO, error budget)
- Blameless postmortem
- Eliminate toil when it is appropriate

## SRE's Mission

- Reliability - Meet the availability targets the users need

- Velocity - Maximize the long-term feature velocity.

- Maintainability - 易于维护

- Efficiency - 高效利用人力和资源

## SLA & SLO & SLI

SLA - a promise, economic incentive, or else, we get paged

SLO - a goal.

SLI- Service Level Indicator

reference:

1. <https://devops.com/sres-stop-asking-your-product-managers-for-slos/>

## The Four Golden Signals

Focus on metrics that tell you insights into the “The Four Golden Signals” of monitoring:

- **Latency**: The time it takes to service a request.
- **Traffic**: How much demand is being placed on your system.
- **Errors**: The rate of failures in your system.
- **Saturation**: How “full” is your system — and critically, how much capacity remains.


## SRE Budgets

- Performance budgets
- Error Budget
  - A service that’s 99.99% available is 0.01% unavailable. That permitted 0.01% unavailability is the service’s error budget.
- Training Budget
- Toil budget

## SRE Role Expectation

1. Set up the platform level monitoring to keep critical applications up and running despite bandwidth outage, and configuration problems.
2. Engage in service capacity planning, software performance analysis and system tunning
3. Collaborate with Infra team to lead platform level operation optimization （AWS，Akamai，F5，Dockers，DB）
4. Conduct on call duties for critical platform issues

## Observability

### Metrics

time series databases like Prometheus, InfluxDb,Graphite.

#### CPU Throttling

`CPU throttling` is a key application performance metric due to the direct correlation between response time and CPU throttling. 

CPU throttling occurs when you configure a **CPU limit** on a container, which can invertedly slow your application’s response time. Even if you have more than enough resources on your underlying node, your container workload will still be throttled because it was not configured properly.


### Logs


Loki, Splunk
### Trace

- Grafana Tempo with open trace protocal OpenTelemetry
- Zipkin — 微服务链路跟踪 https://zipkin.io/pages/quickstart.html
- Jaeger
- OpenTelemetry https://opentelemetry.io/

## What should be monitored

- Service downtime (health check)
- Slow response time
- Errors and crashes events/logs
- Resource usage. Don't waste money on unnecessary resources ( cloud resource watch)
	
https://hackernoon.com/node-js-monitoring-done-right-70418ecbbff9

## Alert & Incident Response

https://engineering.razorpay.com/what-goes-behind-managing-production-alerts-204f186ce865

## SREcon22

### SREcon22 APAC - Move Fast and Learn Things: Principles of Cognition, Teaming, and Coordination

Cognitive Work



## Resource

- <https://github.com/linkedin/school-of-sre>
- Site Reliability Engineering: How Google Runs Production Systems (known as "The SRE Book")
- The Site Reliability Workbook: Practical Ways to Implement SRE (known as "The SRE Workbook")
- Seeking SRE: Conversations About Running Production Systems at Scale
- [SREcon](https://www.usenix.org/conference/srecon14/technical-sessions/presentation/keys-sre) 