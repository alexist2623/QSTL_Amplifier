# THS3491 RGT G≈20 — Altium Rev D 검토본

2026-10-28. [프로젝트](QSTL_THS3491_RGT_G20_RevD.PrjPcb),
[회로도](QSTL_THS3491_RGT_G20_RevD.SchDoc),
[PCB](QSTL_THS3491_RGT_G20_RevD.PcbDoc)를 같은 폴더에 두고 프로젝트를 연다.
Rev C 원본은 그대로 보존했다. 이 버전은 제조 승인본이 아니다.

## 독립 GND 테스트포인트 TP1 제거 (2026-10-28)

출력 커넥터 위쪽 (31.49601, 21.8948 mm)의 **TP1**을 PCB·회로도·BOM에서 제거했다.
패드 Ø1.4779 mm와 드릴 Ø0.9779 mm를 없애고 네 층의 해당 위치를 GND로 복원했다.
하면의 TP1 전용 마스크 보호 영역도 제거해 기존 넓은 GND 노출과 연결했다.
현재 **31개 부품, 83개 패드, 965개 비아, 26개 임베디드 모델**이다.

본 PCB와 회로도 모두 Altium 저장·재열기를 완료했다. 직전 검증본과 모든 객체를
비교해 TP1과 그 자리의 동박·마스크 외에는 변경이 없음을 확인한 **49개 검사**를 통과했다.
독립 DRC는 오류 0, 미연결 0, 기존 RG_DRIVE 아크 경고 1개다.
이전 168개 기능 검사는 당시 파일의 검증 기록으로 보존하며 이번 검사로 재실행했다고 표시하지 않는다.
현재 `verify_and_package.py`는 이 변경 전용의 엄격한 차이 검사를 실행한다.
[제거 전후 그림](review/TP1_removed.png), [현재 검증](review/remove_tp1_check.json),
[변경 정의](remove_tp1_intent.json). 그림은 저장 파일 기반 재렌더링이다.

## 기판 외곽 GND 비아 (2026-10-28)

네 변을 따라 GND 비아 **148개를 추가**하고 기존 비아 50개를 외곽 배열에 활용했다.
현재 총 비아는 **965개**다. 비아 중심은 기판 끝에서 **1.00 mm** 안쪽,
동박 끝은 **0.80 mm** 안쪽이다. 기본 피치는 **1.00 mm**, 외경/드릴은 **0.40/0.20 mm**다.
RF 커넥터의 신호 경로와 핀 이격 때문에 16개 기준 위치를 비웠다.
따라서 커넥터 주변까지 일정 피치로 이어지는 닫힌 배열은 아니다.

새 비아는 네 층 GND에 연결되며 기존 장착 홀 원형 배열과 RF 차폐 비아를 보존한다.
부품·배선·동박 면·L2 개구·하면 마스크·회로도·26개 모델도 유지한다.
이 단계에서 Altium 저장·재열기와 **168개 검사**를 통과했다. 독립 DRC는 오류 0,
미연결 0이며 기존 RF 아크 경고 1개가 남는다.
[외곽 배치 그림](review/board_edge_vias.png), [설계 좌표](edge_via_intent.json),
[저장 파일 검증](review/edge_via_check.json). 그림은 저장 파일 기반 재렌더링이다.

## 장착 홀 원형 GND 비아 (2026-10-28)

H1–H4 장착 홀 각각에 GND 비아 24개를 15° 간격으로 원형 배치했다. 총 **96개 추가**,
이 단계의 총 비아는 **817개**다. 홀 중심에서 비아 중심까지 반경 **3.40 mm**,
비아 외경/드릴 **0.40/0.20 mm**, 이웃 비아 중심 간격은 약 **0.888 mm**다.
검토 기준인 Ø6 mm 나사 머리 외곽에서 비아 동박까지 0.20 mm를 남긴다.
이는 실제 나사/와셔 부품의 치수 검증을 대체하지 않는다.

새 비아는 네 층 GND에 연결된다. 원래 장착 홀은 Ø3.175 mm 비도금 홀로 유지하고,
홀 좌표·기판 외곽·기존 비아·RF 차폐 배열·L3 전원 면·하면 마스크·부품·배선·회로도·모델을 보존했다.
이 단계에서 Altium 저장·재열기와 **160개 검사**를 통과했다. 독립 DRC는 오류 0,
미연결 0이며 기존 RF 아크 경고 1개가 남는다. 아래 그림은 저장 파일 기반 재렌더링이다.
[원형 배치 그림](review/mechanical_hole_via_rings.png),
[설계 좌표](mount_hole_ring_intent.json), [검증 결과](review/mount_hole_ring_check.json).

## RF 3W 차폐 비아 (2026-10-28)

입력 두 경로, 출력 경로 및 RF 부품 주변에 GND 차폐 비아 **98개**를 추가했다.
조건에 맞는 기존 비아 **29개**도 차폐 배열에 활용하며 기존 비아는 모두 보존한다.
이 단계의 총 비아는 **721개**다. 외경/드릴은 0.40/0.20 mm, 기본 배치 피치는 0.90 mm다.

3W 기준은 RF 배선 폭 W=0.3058 mm에 대해 **RF 동박 가장자리–비아 동박 가장자리
최소 0.9174 mm**로 적용했다. 저장된 배치의 최소 간격은 0.91808 mm다.
새 비아는 L1/L2/L3/L4 GND 안에 배치되어 L3 국부 전원 면을 새로 뚫지 않는다.
핀·부품·기존 비아 드릴 이격·전원 면 때문에 배치할 수 없는 17개 기준점은 건너뛰었다.
따라서 0.90 mm는 기본 피치이며 전체 외곽의 최대 간격이나 닫힌 차폐함을 뜻하지 않는다.

RF 배선·아크·패드·부품·회로도·동박 면 외곽·L2 개구·하면 마스크·26개 모델은 유지한다.
이 단계에서 Altium 저장·재열기와 **153개 검사**를 통과했다. 독립 DRC는 오류 0,
미연결 0이며 기존 RF 아크 경고 1개가 남는다. 화면 캡처는 타임아웃으로 검증하지 않았다.
[배치 그림](review/RF_3W_shield_vias.png), [설계값](rf_fence_intent.json),
[저장 파일 검증](review/rf_fence_check.json). 그림은 파일 기반 재렌더링이다.
`RunShapeRepair` 이전 명령의 호환 진입점을 추가했으며, 이전 수정 후보의 진입점은
폐기된 후보를 수정하지 않고 현재 본 PCB만 연다. 현재 저장 검증은 `ShapeRepair`를 사용한다.

양쪽 GND via fence 배치는 [ADI RF 레이아웃 지침](https://www.analog.com/en/resources/technical-articles/pcbs-layout-guidelines-for-rf--mixedsignal.html)을 참고했다.
3W는 사용자가 요청한 배치 기준이며 임피던스/차폐 성능의 EM 해석 결과가 아니다.
[Altium의 3W 설명](https://resources.altium.com/p/microstrip-ground-clearance-how-close-too-close)도
실제 이격 영향은 적층과 전송선 형상에 따라 달라짐을 설명한다.

## L3 국부 전원 면 + GND (2026-10-28 최종 후속)

사용자의 파란 경로를 따라 L3 VCC/VEE를 입력 비아 배열에서 증폭기 주변으로
이어지는 국부 전원 면으로 줄이고 나머지를 GND로 채웠다. 실제 전원 동박은
VCC 77.60 mm², VEE 74.76 mm², GND 2,463.59 mm²다. 전원–GND 최소 이격은
0.204 mm 이상이며 VCC 비아 24개, VEE 비아 23개가 각각 하나의 전원 면에 연결된다.

밀집 GND 비아 줄이 VCC 경로를 막아 해당 stitching 비아 7개를 추가 제거하고
0.80 mm 연결 통로를 확보했다. 이 단계의 총 비아는 **623개**다. C7은 표시 경로 밖에
있으므로 기존 두 전원 연결을 유지하는 폭 0.30 mm의 짧은 분기를 남겼다.
부품·패드·배선·아크·장착 홀·3D 모델·회로도 및 L1/L2/L4 동박과 하면 마스크는 유지한다.

[L3 전후 비교](review/L3_local_power_before_after.png),
[L3 설계값](l3_local_power_intent.json), [저장 파일 검사](review/l3_local_power_check.json).
최종 파일의 Altium 저장·재열기 및 **146개 검사**를 통과했다. 독립 동박 DRC는
오류 0, 미연결 0이며 기존 RG_DRIVE 보조 아크 경고 1개가 남는다. 최신 전체
검사 결과는 `review/validation_summary.json`에 기록했다.

## L2 전용 RF 개구와 하면 GND 노출 (2026-10-28)

사용자 요청에 따라 L3·L4의 기존 RF 국부 개구 6개를 제거했다. L2의 18개 패드별
개구와 기존 3개 국부 개구, 상면 3개 국부 개구는 유지한다. L3의 전원 면 사이
절연 간격과 다른 넷 비아의 정상적인 동박 이격은 유지된다.

VIN_P 면과 겹치거나 가장자리 이격을 침범하는 GND 비아 12개를 제거했다.
이 단계의 비아는 **630개**이며 부품 32개, 패드 84개, 신호 트랙 42개, RF 아크 3개,
내장 모델 26개는 유지한다. 음전원 쪽 비아는 이번 요청 범위에서 변경하지 않았다.

사용자가 선택한 범위에 따라 하면 GND 약 **2,350.23 mm²**를 넓게 노출했다.
부품·커넥터 핀의 수직 투영과 비접지 비아 주변에 최소 0.30 mm 마스크를 남기고,
기판 가장자리에는 약 0.50 mm 띠를 남겼다. U1 중앙 EP 바로 아래도 노출된다.
기존 패드의 납땜용 마스크/페이스트 설정은 유지했다. U1에서 7.134 mm 아래에
있는 사각 H9 패드는 방열판 납땜용이므로 그대로 둔다.

검증은 `review/validation_summary.json`, `review/layer_mask_via_check.json` 및
Altium 저장·재열기 로그를 기준으로 한다. 아래 그림은 저장 파일의 동박·마스크를
다시 그린 것으로 Altium 화면 캡처가 아니다.
[하면 노출·U1 확대·비아 정리](review/bottom_ground_mask_and_vias.png),
[L2/L3/L4 비교](review/RF_layers_L2_L3_L4.png).

## 양쪽 DC 입력 면 확장 완료 (2026-10-28)

후속 요청에 따라 **VIN_P와 VIN_N 모두** 잭과 입력 필터를 잇는 ㄱ자 전원 면으로 확장했다.
기존 잭 위치를 기준으로 각각 면을 만들었으며, 핀·부품·비아·RF 배선·필터 위치는 유지했다.
두 잭 모두 해당 전원 면과 2번 GND 패드 사이 최소 간격은 약 0.2055 mm,
3번 미사용 스위치 패드와는 1.10 mm다. GND의 L2/하면 연결과 3번의 PCB 미연결을 확인했다.
면 외곽 면적은 VIN_P 99.47 mm², VIN_N 143.26192 mm²다.

최종 Altium 저장·닫기·재열기와 **127개 검사**를 통과했다. 독립 DRC는 오류 0,
미연결 0이며 기존 RF 아크 경고 1개가 남는다. 26개 내장 모델의 배치도 유지됐다.
[양쪽 비교 그림](review/dc_planes_both.png), [양쪽 검사 결과](review/dc_plane_check.json),
[현재 외곽 설계값](dc_plane_intent.json).

## VIN_P 면 확장 및 잭 핀 재확인 (2026-10-28 후속)

사용자가 표시한 파란 외곽에 맞춰 J9의 VIN_P 면을 ㄱ자 형태로 확장했다.
이 요청은 핀 이동이 아니라 동박 면 변경으로 확인했다. 원래 입력 면 46.00 mm²를
99.47 mm² 외곽으로 넓혔으며, C1/L1 중심을 지나는 필터 경계는 유지한다.
부품·핀·배선·비아·장착 홀·L2 개구·음전원 입력·회로도는 변경하지 않았다.

PJ-102AH 제조사 도면의 상면 핀 배치와 일치한다. 1번은 중심 접점, 2번은 외곽 접점이다.
옆의 3번은 **플러그를 빼면 2번과 닫히고 꽂으면 열리는 스위치 접점**이다.
PCB에서는 3번에 넷이나 배선을 추가하지 않았다. 새 VIN_P 동박은 2번 GND 패드와
최소 0.2055 mm, 3번 패드와 1.10 mm 떨어진다. 2번의 L2 및 하면 GND 연결은 유지된다.

최종 파일을 Altium에서 저장·닫기·재열기하고 125개 검사를 통과했다.
독립 동박 DRC는 오류 0, 미연결 0, 기존 RF 아크 경고 1개다.
[변경 및 핀 설명 그림](review/dc_plane_pinout.png), [검사 결과](review/dc_plane_check.json),
[면 외곽 설계값](dc_plane_intent.json), [제조사 도면 2쪽](https://www.sameskydevices.com/product/resource/pj-102ah.pdf).

## DC 어댑터 입력만 사용 (2026-10-28)

사용자의 최종 요청에 따라 바나나 잭 배치를 취소하고 **DC 배럴 잭 두 개**를 적용했다.
기존 전원 납땜 패드 J4/J5/J6/J8을 회로도·PCB·BOM에서 제거했다.

| 입력 | 부품 | 중심 접점 1 | 외곽 접점 2 | 방향 |
| --- | --- | --- | --- | --- |
| +15 V | J9, Same Sky PJ-102AH | VIN_P / +15 V | GND | 기판 위쪽 |
| −15 V | J10, Same Sky PJ-102AH | VIN_N / −15 V | GND | 기판 아래쪽 |

두 잭은 5.5/2.1 mm 플러그용이며 접점 3은 미사용 스위치 단자다.
잭 자체 정격은 24 VDC / 5 A다. **J10은 중심 음극 전원이 필요하다.**
일반적인 중심 양극 +15 V 어댑터를 그대로 꽂아 −15 V로 바꾸는 회로는 없다.
전압 및 중심·외곽 극성을 상면 실크에 표시했다.
두 입력 모두 기존 L1/L2 필터 앞의 VIN_P/VIN_N에 연결된다.

기판은 41.65601 × 68.58 mm로 유지했다. 장착 홀, RF 배선, 입력 필터·직사각형 면,
18개 L2 RF 패드 개구 및 VCC/VEE 비아 배열은 그대로다.
새 잭/전원 배선과 겹치는 GND 비아 8개만 제거했다.
이 단계는 32개 PCB 부품, 84개 패드, 642개 비아, 42개 신호 트랙, 26개 내장 모델이었다.
회로도 핀/배선/넷 라벨을 비교했고, 실제 Altium 저장·닫기·재열기 후
123개 설계 검사를 통과했다. 독립 동박 DRC는 오류 0, 미연결 0이며
기존 0.0089 mm RF 아크 경고 1개가 남는다. Altium 화면 캡처 및 자체 ERC/DRC는 검증하지 않았다.

PJ-102AH는 제조사 MPN을 지정한 **수동 THT 조립** 품목이다.
JLC의 C9900001188 서비스 항목을 재고 증거로 사용하지 않았으며, 실제 부품 공급/조립 가능 여부는 미확인이다.
모델은 제조사 치수도에 맞춘 단순화 형상이다. 기존 실장 모델과의 최소 간격은 J9 3.92 mm,
J10 5.1352 mm이며 장착 홀 주위 Ø6 mm 나사 머리 영역도 검사했다.

[배치·극성 그림](review/dc_input_layout.png), [입력 회로도 그림](review/dc_input_schematic.png),
[3D 그림](review/component_3d_overview.png), [설계값](dc_inputs_intent.json),
[전기·보존 검사](review/dc_inputs_check.json), [간섭 검사](review/dc_mechanical_check.json).
그림은 저장된 형상을 다시 렌더링한 자료다. 이전 후보는 `staging/`에 보존했으며
현재 프로젝트는 위의 RevD 파일을 사용한다.

## 출력 부하 제거 및 3D 모델 (2026-10-27)

- 출력단 R15(1 MΩ), 두 패드와 해당 L2 패드 개구를 제거했다. R14–J3 출력 배선과 기존 GND stitching 비아는 유지했다.
- 회로도 R15와 전용 분기선·GND 라벨을 제거하고 BOM/CPL을 갱신했다.
- `TI RF geometry / JLC 4L adaptation`, `QSTL / THS3491 RGT / REV D` 설명용 실크 두 줄을 제거했다. 전원·TEMP/GND 표시는 유지했다.
- 24개 실장 부품에 10종 STEP 모델을 PCB 내부에 포함했다. 외부 STEP 경로가 없어도 모델을 읽을 수 있다. H9는 치수에 맞춘 단순화 방열판 모델이며 일반 수동부품은 표준 패키지 모델이다.
- Altium 저장·닫기·재열기 후 24개 모델의 부품 연결, 위치·회전·실장면을 검사했다. [3D 검토 그림](review/component_3d_overview.png)은 검증한 STEP 배치를 다시 렌더링한 그림이다. 화면 캡처 도구의 타임아웃으로 Altium 화면 자체는 확인하지 못했다.

[모델 출처·정밀도](models3d/README.md), [모델 검증](review/component_3d_check.json), [R15/실크 변경 검증](review/output_load_removal.json).
기존 `entry_plane_array_check.json`, `shape_regression_check.json` 등은 해당 수정 시점의 기록이다. 현재 파일 검증은 `validation_summary.json`을 기준으로 한다.

## 반영한 변경

- C5/C6를 TI EVM의 기록된 위치·방향으로 복원했다. C3/C4는 입력 필터 쪽으로 옮겼다.
- C5 VCC 면은 VS+13/14, 커패시터 전원 패드, 병렬 비아만 포함한다. C6도 같은 폭의 국부 전원 면을 사용한다.
- PD16은 0.15 mm L1 배선과 별도 0.40/0.20 mm 관통 비아로 L3 VCC에 연결한다. NC15는 주변 L1 GND 면과 연속적으로 연결된다.
- C6와 겹치던 TEMP 배선을 옮겼다. 후속 입력부 수정에서는 비드와 겹치는 보조 전원 비아 12개와 GND stitching 비아 4개를 추가 제거했다.
- R15를 제외한 RF 소자 위치·저항 값과 RF 곡선 3개를 유지했다. 회로도에서는 R15와 전용 분기만 제거했다. 실장 좌표와 via-in-pad 공정표를 새 배치에 맞춰 갱신했다.

## 입력부 직사각형 및 L2 RF 패드 개구 수정

사용자 요청에 따라 ±15 V 입력부를 180° 대칭으로 수정했다. C2를 위로 1.87961 mm,
C4와 필터 비드 L2를 위로 1.026 mm 이동하고, C1/C3/L1에는 대칭 이동을 적용했다.
C1/C2는 입력 동박 경계, C3/C4는 필터 후단 동박 경계가 **부품 중심**을 지나도록 했다.
네 폴리곤은 직사각형이고, 커패시터 GND 패드는 전원 면 밖에 있다.
좌표와 경계는 [입력부 설계값](input_rectangle_intent.json) 및 [검증 결과](review/input_rectangle_and_L2_check.json), 그림은
[직사각형 배치](review/input_rectangle_verification.png)에 있다.

추가 제거한 비아는 보조 전원 비아 12개와 GND stitching 비아 4개다.
커패시터와 비드의 의도된 via-in-pad는 새 패드 위치를 따라 이동했으며 이 단계의 비아는 621개였고, 후속 배열 추가로 현재 총 650개다.
필터 후단에는 각 전원 레일당 기존 패드 내 비아 2개와 아래의 새 배열 비아 16개가 있다.

L2의 기존 개구가 RF 패드 전체를 덮지 못하는 문제도 보완했다. R1–R7, R14,
U1 신호 I/O의 **신호 패드 18개** 아래에 패드 외곽 + 0.10 mm 개구를 추가했다.
이 단계에서는 기존 다층 국부 개구를 유지했으며, 이후 사용자 요청으로 L3/L4 개구만 제거했다.
접지 패드와 U1 방열 패드 연결은 유지한다. L2 동박과 패드
투영 면적의 교집합이 0이고 L2 GND가 하나로 연결됨을 저장 파일 재판독으로 검사한다.
개구는 실제 Altium polygon cutout 객체로 저장되며 채워진 동박에만 의존하지 않는다.
[패드별 개구](review/rf_pad_windows.json), [L2 그림](review/L2_RF_pad_clearance.png).

TI는 신호 I/O 주변의 GND·전원 평면 개구를 권고한다
([THS3491 데이터시트 §10.4.1](https://www.ti.com/lit/ds/symlink/ths3491.pdf)).
이번 0.10 mm 여유는 사용자의 L2 요청을 구현한 설계값이며 SI/EM 최적화 결과는 아니다.

## 입력 필터 전원 면 확장 및 비아 배열

표시된 VEE 면을 오른쪽으로 확장하고 반대편 VCC에는 180° 대칭으로 적용했다.
사용자의 “VSS”는 현재 회로에 해당 넷이 없어 반대편 VCC(+15 V)로 해석했다.
두 면의 폭은 **2.8 → 6.0 mm**, 높이는 3.66139 mm다. 커패시터 중심을 지나는
경계와 부품 위치는 유지한다. 각 레일에 **4×4 비아 배열 16개**, 합계 32개를 추가했다.
주변 stitching 비아와 같은 **패드 Ø0.40 / 드릴 Ø0.20 mm**, 배열 피치 0.80 mm다.
전원 면과 간섭하는 VEE 쪽 GND stitching 비아 3개를 제거하여 총 비아는 650개다.

새 비아는 각각 VCC/VEE에 배정하고 L1 면 및 L3 전원 면에 연결한다. L2에서는
전원 비아 주위로 GND 간격을 확보한다. RF 신호 패드 18개 아래의 L2 개구는 유지한다.
[배열 검증 그림](review/entry_plane_via_arrays.png), [좌표·검사 결과](review/entry_plane_array_check.json).
이 그림은 저장된 네이티브 파일을 재판독한 렌더링이며 Altium 화면 캡처는 아니다.

## Altium 로드 오류·패드 레이어 수정

사용자 스크린샷의 `Tracks6 / Creating InternalPlaneLayer(0)` 오류는 트랙의
확장 레이어 ID를 **byte 41 대신 40**에 쓰던 저장 코드가 원인이었다. 상면 ID가
`0x01010000`으로 잘못 해석됐다. 신호 트랙 38개와 외곽 트랙 4개를 수정했고,
외곽의 Mechanical 1 ID도 바로잡았다. RF 좌표·폭·넷은 유지했다.

패드는 legacy 층만 변경하고 확장 ID는 템플릿의 Bottom 값으로 남겨두고 있었다.
**상면 66개·하면 7개·관통 11개**의 두 레이어 정의를 일치시켰다.
이 오류는 legacy 층을 우선 읽는 독립 판독기에서 드러나지 않았다. 재발 방지를
위해 두 정의를 직접 대조하는 [검사 코드](tools/check_layer_encoding.py)를 추가했다.

최종 PCB는 **Altium Designer 25.8.1에서 열기 → 저장 → 닫기 → 재열기**를
완료했다. 내부 API가 패드 82개와 트랙 42개를 확인했다. Altium 저장 과정에서
`FileVersionInfo`와 텍스트 등 기본 데이터를 정상화했고, 최종 재열기 때 새
`.PcbDoc.htm` 변환 보고서는 생성되지 않았다.
[앱 검증 로그](review/altium_native_check.txt), [파일 해시가 포함된 결과](review/altium_application_check.json).
화면 캡처 도구는 타임아웃되어 픽셀 단위 확인은 수행하지 못했다.

## 패드 형상 및 C7 동박 후속 수정

사용자의 최종 형상 요청에 따라 R15 삭제 후 남은 19개 패드(R14 2개, U1 17개)를
**직각 사각형(Rectangle), 모서리 반경 0**으로 수정했다. 앞선 둥근 사각형 복원은
이 수정으로 대체된다. Altium의 `eRectangular` 형상과 레이어별 반경 0을 적용했다.
패드 목록을 수집한 뒤 별도 루프에서
수정하며, Altium 기본 저장으로 정리한 파일에서 실행한다. 수정 중 iterator를
계속 사용하지 않는다. 저장·닫기·재열기 후 **19개 형상 및 반경값 모두 통과**했다.

패드 크기·위치·넷은 그대로다. 직각 모서리의 구리 면적까지 반영해 주변
폴리곤을 다시 채우고 독립 DRC를 수행했다. 이전 둥근 패드 파일과 검증 자료는
`staging/pre_square_pad_repair_20261022/`에 백업했다.

C7의 불필요한 `L1_C7_VEE` 및 비어 있던 `L1_C7_VCC` 폴리곤을 제거하고
주변 GND 동박을 다시 채웠다. C7 두 패드 안의 VCC/VEE 비아와 L3 연결은 유지했다.
[형상 검증 그림](review/pad_shape_verification.png)은 저장 후 독립 재판독한 동박·패드의
렌더링이며 Altium 화면 캡처는 아니다. [현재 패드 판독 기록](review/native_import_check.json). `pad_shape_repair.json`은 R15 삭제 전의 이력이다.

[THS4021EVM 외곽·장착홀 비교](review/mechanical_compare_THS4021EVM.png)와
[수치·출처·추정 방법](review/mechanical_compare_THS4021EVM.json)도 추가했다.
Rev D는 41.656 × 68.580 mm, 홀 간격은 31.496 × 58.420 mm다. TI 보드 크기는
약 43.18 × 35.56 mm이며, 홀 간격 약 34.9 × 27.2 mm는 치수가 없는 참고 그림을
정규화한 추정값이다. TI 그림 자체가 not-to-scale이므로 가공 치수로 사용할 수 없다.

수정 전 Rev D PCB와 기존 변환 보고서는 로컬 `staging/pre_layer_encoding_repair_20261022/`에
백업했다. 이 폴더는 Git 제외 대상이다. Rev C 원본은 수정하지 않았으므로 해당
과거 PCB를 직접 열면 같은 저장 형식 오류가 남아 있다. 현재 검토에는 Rev D를 사용한다.

## 스택 메타데이터 정리

Rev C에는 실제 JLC04161H-7628 **4층 rigid** V9 스택과 함께 이전 생성용 템플릿의
**Two copper flex** V8 스택·폴리이미드 설정이 남아 있었다. Rev D는 V8/V9의
스택 이름, ID, 층 구성, 재질 및 rigid 속성을 일치시켰다.
[수정 기록](review/layer_metadata_repair.json).

`Internal Plane 1–16`은 활성 구리층이 아닌 legacy 예약 슬롯이다. 이 슬롯은
이전 판독기의 호환성을 위해 유지되며 NEXT/PREV는 모두 0, 넷은 No Net이다.
현재 활성층은 Top → Mid1 → Mid2 → Bottom으로, L2 GND와 L3 VCC/VEE는
양각 폴리곤으로 구현되어 있다. 음각 Internal Plane으로 임의 변환하지 않았다.
[Altium의 내부 평면 설명](https://www.altium.com/documentation/altium-designer/pcb/internal-power-split-planes).

위 스택 정리는 별도 호환성 수정이며, `Tracks6` 예외의 직접 원인은 앞서 설명한
바이너리 필드 위치 오류다. Layer Stack Manager의 시각적 확인은 남아 있다.

## 검증 결과와 한계

| 검사 | 결과 |
|---|---|
| 수정 기하의 독립 DRC | 오류 0, 미연결 0, 경고 1 |
| 생성된 PcbDoc를 다시 읽은 동박의 DRC | 오류 0, 미연결 0, 경고 1 |
| 네이티브 기하 대조 | 4층, 부품 34, 패드 82, 비아 650, RF arc 3; 불일치 0 |
| 요구사항·동박 면적·원본 보존·형상·앱 저장 확인 | 121개 통과 |
| TEMP 헤더 피치 | 2.54 mm |
| Altium 앱 열기·저장·재열기 | 성공, 패드 층·개수 및 직각 사각형 19개·반경 0 확인 |
| Altium 앱 ERC·repour·DRC | 미검증 |

경고 1개는 TI 원본에서 유지된 약 0.0089 mm RG_DRIVE 보조 arc의 끝점이다.
주 RF 경로와 중첩되며 Rev C에도 존재한다. [검증 요약](review/validation_summary.json),
[기하 DRC](review/geometry_drc.txt), [네이티브 동박 DRC](review/native_audit_drc.txt),
[네이티브 판독 결과](review/native_import_check.json).

독립 검사는 설치된 KiCad 6.0.10의 판독기·동박 채움·DRC 엔진으로 수행했다.
초기 Rev C 기하 판독에는 Texts6를 제외한 복사본이 필요했다. 현재 최종 Rev D는
Altium이 저장한 **전체 파일을 텍스트까지 포함해** 재판독했다. 동박은 제외하거나
수정하지 않았다. 재판독 DRC에서는 동박을 다시 채우지 않았으며, 판독기가 전달하지
않는 패드 연결 규칙을 검사본에만 재적용했다. 이는 Altium 자체 DRC와 다르다.

C7 두 전원 패드는 패드 내 비아를 통해 연결되며, 불필요한 작은 폴리곤은 제거했다.
BOM 구매 코드와 재고는 다시 조사하지 않았다.
열·SI·PI·EMC, 스택 제조 가능 여부 및 조립 공정 확인은 남아 있다. Gerber를
발행하지 않았다.

## 검토 그림과 조립 자료

- [L1 전체](review/layout_L1.png), [U1 주변](review/layout_core.png),
  [PD16/NC15 확대](review/layout_PD_NC.png), [L3 전원](review/layout_L3.png)
- [BOM](assembly/BOM_REVIEW.csv), [SMT 실장 좌표](assembly/CPL_SMT_REVIEW.csv),
  [via-in-pad 공정](assembly/VIA_IN_PAD_PROCESS_REVIEW.csv)

그림은 네이티브 파일에서 다시 읽은 동박으로 렌더링했다. Altium 화면 캡처가
아니다. 부품·패드·트랙 위치는 별도로 네이티브 판독 결과와 대조했다.

## 재현·검증 도구

현재 파일의 검증 순서는 `record_native_verification.py` → KiCad Python의
`import_for_audit.py`, `audit_native.py` → `audit_dc_inputs.py`, `audit_dc_plane.py`,
`audit_3d_models.py` → `verify_and_package.py`다. 네이티브 검증 로그는
`review/native_shape_repair/ShapeRepair.PrjScr`의 `ShapeRepair`를 Altium에서
실행해 생성한다. 모델 검사는 저장 파일과 같은 SHA-256의 기하 검사 결과를 요구한다.

`prepare_geometry.py`와 `native_update.py`는 R15 삭제 전 기본 Rev D의 생성 도구다.
현재 출력단 변경은 `output_load_intent.json`에 기록되어 있으며,
`make_remove_r15_script.py`로 생성한 네이티브 스크립트가 PCB의 R15·L2 개구와
회로도의 전용 분기를 제거한다. 제거를 반영한 `review/intended_geometry.json`을
`fill_and_check.py`로 채우고, `refresh_native_copper.py`로 기존 부품·모델·규칙을
보존한 검사 복사본을 만든다. 이 복사본도 Altium 저장·닫기·재열기를 거쳐야 한다.
현재 최종 로그는 `review/altium_native_check.txt`다.

`models3d/README.md`에 STEP 출처와 모델 생성·적용 도구를 설명했다.
`make_shape_script.py --assembly-finalization`은 설명용 실크를 제거하고,
남은 19개 직각 패드 및 26개 모델을 재열기 후 확인한다. 미저장 편집이 있으면 중단한다.

회로도는 Rev C에서 R15와 전용 분기선 두 개, 해당 GND 라벨을 제거한 뒤,
전원 패드 네 개를 DC 입력 두 개로 교체했다. 나머지 부품·핀·배선·넷 라벨은
독립 대조했다. `output_load_removal.json`은 DC 입력 변경 전 검증 기록이고,
`dc_inputs_check.json`이 그 기록과 현재 파일을 연결한다. Rev C 원본은 보존한다.
`staging/`은 검사용이며 최종 Altium 프로젝트에 포함되지 않는다.
