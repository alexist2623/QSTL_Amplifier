# THS3491 RGT G≈20 — Altium Rev D 검토본

2026-10-22. [프로젝트](QSTL_THS3491_RGT_G20_RevD.PrjPcb),
[회로도](QSTL_THS3491_RGT_G20_RevD.SchDoc),
[PCB](QSTL_THS3491_RGT_G20_RevD.PcbDoc)를 같은 폴더에 두고 프로젝트를 연다.
Rev C 원본은 그대로 보존했다. 이 버전은 제조 승인본이 아니다.

## 반영한 변경

- C5/C6를 TI EVM의 기록된 위치·방향으로 복원했다. C3/C4는 입력 필터 쪽으로 옮겼다.
- C5 VCC 면은 VS+13/14, 커패시터 전원 패드, 병렬 비아만 포함한다. C6도 같은 폭의 국부 전원 면을 사용한다.
- PD16은 0.15 mm L1 배선과 별도 0.40/0.20 mm 관통 비아로 L3 VCC에 연결한다. NC15는 주변 L1 GND 면과 연속적으로 연결된다.
- C6와 겹치던 TEMP 배선을 옮겼다. 후속 입력부 수정에서는 비드와 겹치는 보조 전원 비아 12개와 GND stitching 비아 4개를 추가 제거했다.
- RF 소자 위치, RF 곡선 3개, 넷 연결, 저항 값, 회로도는 유지했다. 실장 좌표와 via-in-pad 공정표를 새 배치에 맞춰 갱신했다.

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

L2의 기존 개구가 RF 패드 전체를 덮지 못하는 문제도 보완했다. R1–R7, R14/R15,
U1 신호 I/O의 **신호 패드 19개** 아래에 패드 외곽 + 0.10 mm 개구를 추가했다.
기존 다층 국부 개구, 접지 패드, U1 방열 패드 연결은 유지했다. L2 동박과 패드
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
전원 비아 주위로 GND 간격을 확보한다. RF 신호 패드 19개 아래의 L2 개구는 유지한다.
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
완료했다. 내부 API가 패드 84개와 트랙 42개를 확인했다. Altium 저장 과정에서
`FileVersionInfo`와 텍스트 등 기본 데이터를 정상화했고, 최종 재열기 때 새
`.PcbDoc.htm` 변환 보고서는 생성되지 않았다.
[앱 검증 로그](review/altium_native_check.txt), [파일 해시가 포함된 결과](review/altium_application_check.json).
화면 캡처 도구는 타임아웃되어 픽셀 단위 확인은 수행하지 못했다.

## 패드 형상 및 C7 동박 후속 수정

사용자의 최종 형상 요청에 따라 21개 패드(R14 2개, R15 2개, U1 17개)를
**직각 사각형(Rectangle), 모서리 반경 0**으로 수정했다. 앞선 둥근 사각형 복원은
이 수정으로 대체된다. Altium의 `eRectangular` 형상과 레이어별 반경 0을 적용했다.
패드 목록을 수집한 뒤 별도 루프에서
수정하며, Altium 기본 저장으로 정리한 파일에서 실행한다. 수정 중 iterator를
계속 사용하지 않는다. 저장·닫기·재열기 후 **21개 형상 및 반경값 모두 통과**했다.

패드 크기·위치·넷은 그대로다. 직각 모서리의 구리 면적까지 반영해 주변
폴리곤을 다시 채우고 독립 DRC를 수행했다. 이전 둥근 패드 파일과 검증 자료는
`staging/pre_square_pad_repair_20261022/`에 백업했다.

C7의 불필요한 `L1_C7_VEE` 및 비어 있던 `L1_C7_VCC` 폴리곤을 제거하고
주변 GND 동박을 다시 채웠다. C7 두 패드 안의 VCC/VEE 비아와 L3 연결은 유지했다.
[형상 검증 그림](review/pad_shape_verification.png)은 저장 후 독립 재판독한 동박·패드의
렌더링이며 Altium 화면 캡처는 아니다. [수정·검증 기록](review/pad_shape_repair.json).

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
| 네이티브 기하 대조 | 4층, 부품 35, 패드 84, 비아 650, RF arc 3; 불일치 0 |
| 요구사항·동박 면적·원본 보존·형상·앱 저장 확인 | 120개 통과 |
| TEMP 헤더 피치 | 2.54 mm |
| Altium 앱 열기·저장·재열기 | 성공, 패드 층·개수 및 직각 사각형 21개·반경 0 확인 |
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

## 재현 도구

`tools/`는 체크인된 Rev C, 계획 JSON 및 `input_rectangle_intent.json`을 입력으로 사용한다. 과거 PC의
캐리어 파일이나 TI 임시 import는 필요 없다. Windows, Python 3(olefile 0.47,
shapely, matplotlib), KiCad 6.0.10의 Python/pcbnew가 필요하다.

1. `prepare_geometry.py`로 계획을 적용한다.
2. `native_update.py --audit-source <RevC.PcbDoc> --output <새 검사복사본.PcbDoc>`로
   검사본을 만들고 KiCad의 Altium importer로 읽어 `staging/baseline_import.kicad_pcb`에 저장한다.
3. KiCad Python으로 `fill_and_check.py`를 실행한다.
4. 일반 Python으로 `native_update.py --output <새 RevD.PcbDoc>`를 실행한다.
   기존 대상 파일을 덮어쓰지 않는다.
5. `make_shape_script.py --pcb <PCB 절대 경로> --script-dir <스크립트 폴더> --log <로그 경로>`로
   형상 복원·검증 스크립트를 생성한다. `review/native_shape_repair/ShapeRepair.PrjScr`의
   `ShapeRepair`가 현재 파일에 실제로 사용된 스크립트다. Altium 기본 저장 → 패드 형상·반경
   복원 → 저장·닫기·재열기 → 21개 형상 검사 순으로 실행한다. 미저장 편집이 있으면 중단한다.
   **native_update.py 생성본만 전달하지 말고 이 Altium 단계를 완료해야 한다.**
6. 일반 Python으로 `check_layer_encoding.py <PCB>`와 `record_native_verification.py`를 실행한다.
7. KiCad Python으로 `import_for_audit.py`, `audit_native.py`를 실행한다. 저장된 전체 Rev D를
   읽으며 `staging/native_roundtrip.kicad_pcb` 및 원본 SHA-256을 기록한다.
8. 일반 Python으로 `verify_and_package.py`, `render_review.py`를 실행한다.
   검증 스크립트는 문서 3개가 이 폴더에 있는 상태를 전제로 한다.

Altium 회로도는 Rev C와 바이트 단위로 동일한 복사본이다. 프로젝트 문서 경로와
PCB의 source hierarchy는 Rev D 파일 이름을 참조한다. `staging/`은 검사용이며
최종 Altium 프로젝트에 포함되지 않는다.
