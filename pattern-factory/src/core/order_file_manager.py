# Order File Manager and Output Generation
# Version 6.4.3 Implementation

import os
import json
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class PieceInfo:
    """Information about a pattern piece"""

    name: str
    contour: List[Tuple[float, float]]
    bounding_box: Tuple[float, float, float, float]  # min_x, min_y, max_x, max_y
    notches: Optional[List[Tuple[float, float]]] = None
    grainline: Optional[Dict] = None
    piece_number: int = 0
    total_pieces: int = 0


class OrderFileManager:
    """
    Manages folder structure and file operations for orders.
    Ensures order number continuity and proper naming conventions.
    """

    def __init__(self, base_dir: str = "DS-speciale/out/orders"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def generate_order_id(self, customer_id: Optional[str] = None) -> str:
        """Generate unique order ID: SDS-YYYYMMDD-NNNN-R"""
        today = datetime.now()
        date_str = today.strftime("%Y%m%d")

        # Find next sequential number for today
        existing_orders = list(self.base_dir.glob(f"SDS-{date_str}-*"))
        if existing_orders:
            # Extract numbers and find max
            numbers = []
            for order_path in existing_orders:
                match = re.search(rf"SDS-{date_str}-(\d{{4}})-[A-Z]", order_path.name)
                if match:
                    numbers.append(int(match.group(1)))
            next_num = max(numbers) + 1 if numbers else 1
        else:
            next_num = 1

        order_id = f"SDS-{date_str}-{next_num:04d}-A"
        return order_id

    def create_order_folder(
        self,
        order_id: str,
        customer_id: Optional[str] = None,
        create_subdirs: bool = True,
    ) -> Path:
        """Create folder structure for order"""
        order_folder = self.base_dir / order_id
        order_folder.mkdir(parents=True, exist_ok=True)

        if create_subdirs:
            # Create subdirectories
            (order_folder / "pieces").mkdir(exist_ok=True)
            (order_folder / "previews").mkdir(exist_ok=True)
            (order_folder / "history" / "rev_A").mkdir(parents=True, exist_ok=True)

            # Create order info file
            info = {
                "order_id": order_id,
                "customer_id": customer_id,
                "created_at": datetime.now().isoformat(),
                "revision": "A",
                "folder_path": str(order_folder),
            }

            with open(order_folder / "order_info.json", "w") as f:
                json.dump(info, f, indent=2)

        logger.info(f"Created order folder: {order_folder}")
        return order_folder

    def get_order_folder(self, order_id: str) -> Path:
        """Get path to order folder"""
        return self.base_dir / order_id

    def save_plt(self, order_id: str, plt_content: str) -> Path:
        """Save PLT file with proper naming"""
        folder = self.get_order_folder(order_id)
        file_path = folder / f"{order_id}.plt"

        with open(file_path, "w") as f:
            f.write(plt_content)

        logger.info(f"Saved PLT: {file_path}")
        return file_path

    def save_pds(self, order_id: str, pds_content: bytes) -> Path:
        """Save PDS file with proper naming"""
        folder = self.get_order_folder(order_id)
        file_path = folder / f"{order_id}.pds"

        with open(file_path, "wb") as f:
            f.write(pds_content)

        logger.info(f"Saved PDS: {file_path}")
        return file_path

    def save_dxf(self, order_id: str, dxf_content: str) -> Path:
        """Save DXF file with proper naming"""
        folder = self.get_order_folder(order_id)
        file_path = folder / f"{order_id}.dxf"

        with open(file_path, "w") as f:
            f.write(dxf_content)

        logger.info(f"Saved DXF: {file_path}")
        return file_path

    def save_metadata(self, order_id: str, metadata: dict) -> Path:
        """Save metadata JSON file"""
        folder = self.get_order_folder(order_id)
        file_path = folder / f"{order_id}_metadata.json"

        with open(file_path, "w") as f:
            json.dump(metadata, f, indent=2)

        logger.info(f"Saved metadata: {file_path}")
        return file_path

    def save_qc_report(self, order_id: str, qc_report: dict) -> Path:
        """Save QC report JSON file"""
        folder = self.get_order_folder(order_id)
        file_path = folder / f"{order_id}_qc_report.json"

        with open(file_path, "w") as f:
            json.dump(qc_report, f, indent=2)

        logger.info(f"Saved QC report: {file_path}")
        return file_path

    def save_production_log(self, order_id: str, log_content: str) -> Path:
        """Save production log file"""
        folder = self.get_order_folder(order_id)
        file_path = folder / f"{order_id}_production.log"

        with open(file_path, "w") as f:
            f.write(log_content)

        logger.info(f"Saved production log: {file_path}")
        return file_path

    def save_nesting_report(self, order_id: str, nesting_data: dict) -> Path:
        """Save nesting report JSON file"""
        folder = self.get_order_folder(order_id)
        file_path = folder / f"{order_id}_nesting.json"

        with open(file_path, "w") as f:
            json.dump(nesting_data, f, indent=2)

        logger.info(f"Saved nesting report: {file_path}")
        return file_path

    def save_individual_piece(
        self, order_id: str, piece: PieceInfo, format: str = "pds"
    ) -> Path:
        """Save individual piece file"""
        folder = self.get_order_folder(order_id) / "pieces"

        # Format: {ORDER_ID}_piece_XXX_{name}.{ext}
        piece_name = piece.name.replace(" ", "_").upper()
        file_name = (
            f"{order_id}_piece_{piece.piece_number:03d}_{piece_name}.{format.lower()}"
        )
        file_path = folder / file_name

        # Content generation based on format
        if format.lower() == "pds":
            content = self._generate_piece_pds(piece)
            with open(file_path, "wb") as f:
                f.write(content)
        elif format.lower() == "dxf":
            content = self._generate_piece_dxf(piece)
            with open(file_path, "w") as f:
                f.write(content)

        logger.info(f"Saved piece file: {file_path}")
        return file_path

    def _generate_piece_pds(self, piece: PieceInfo) -> bytes:
        """Generate PDS content for single piece (simplified)"""
        # This is a placeholder - actual implementation would use PDS format
        content = f"PDS|PIECE|{piece.name}|{piece.piece_number}\n"
        for point in piece.contour:
            content += f"POINT|{point[0]}|{point[1]}\n"
        return content.encode("utf-8")

    def _generate_piece_dxf(self, piece: PieceInfo) -> str:
        """Generate DXF content for single piece (simplified)"""
        # This is a placeholder - actual implementation would use proper DXF format
        lines = [
            "0",
            "SECTION",
            "2",
            "ENTITIES",
            "0",
            "LWPOLYLINE",
            "8",
            "PIECE",
            "90",
            str(len(piece.contour)),
            "70",
            "1",
        ]

        for point in piece.contour:
            lines.extend(["10", str(point[0]), "20", str(point[1])])

        lines.extend(["0", "ENDSEC", "0", "EOF"])
        return "\n".join(lines)

    def get_all_files(self, order_id: str) -> Dict[str, Path]:
        """Get all file paths for an order"""
        folder = self.get_order_folder(order_id)

        files = {
            "folder": folder,
            "plt": folder / f"{order_id}.plt",
            "pds": folder / f"{order_id}.pds",
            "dxf": folder / f"{order_id}.dxf",
            "metadata": folder / f"{order_id}_metadata.json",
            "qc_report": folder / f"{order_id}_qc_report.json",
            "production_log": folder / f"{order_id}_production.log",
            "nesting_report": folder / f"{order_id}_nesting.json",
            "pieces_folder": folder / "pieces",
            "previews_folder": folder / "previews",
        }

        return files

    def archive_order(self, order_id: str) -> Path:
        """Archive completed order"""
        order_folder = self.get_order_folder(order_id)
        archive_dir = self.base_dir / "archive"
        archive_dir.mkdir(exist_ok=True)

        archive_path = archive_dir / order_id

        # Move order to archive
        import shutil

        shutil.move(str(order_folder), str(archive_path))

        logger.info(f"Archived order {order_id} to {archive_path}")
        return archive_path


class EnhancedOutputGenerator:
    """Generates all output files with proper labeling and formatting"""

    def __init__(self, file_manager: OrderFileManager):
        self.file_manager = file_manager

    def generate_all_outputs(
        self,
        order_id: str,
        pieces: List[PieceInfo],
        nesting_result: dict,
        metadata: dict,
    ) -> Dict[str, Path]:
        """Generate all required output files for an order"""

        outputs = {}

        # 1. Generate PLT with labels
        plt_content = self._generate_labeled_plt(order_id, pieces)
        outputs["plt"] = self.file_manager.save_plt(order_id, plt_content)

        # 2. Generate PDS with labels
        pds_content = self._generate_labeled_pds(order_id, pieces)
        outputs["pds"] = self.file_manager.save_pds(order_id, pds_content)

        # 3. Generate DXF with labels
        dxf_content = self._generate_labeled_dxf(order_id, pieces)
        outputs["dxf"] = self.file_manager.save_dxf(order_id, dxf_content)

        # 4. Save individual pieces
        for piece in pieces:
            self.file_manager.save_individual_piece(order_id, piece, "pds")
            self.file_manager.save_individual_piece(order_id, piece, "dxf")

        # 5. Save metadata
        outputs["metadata"] = self.file_manager.save_metadata(order_id, metadata)

        # 6. Save nesting report
        nesting_report = {
            "order_id": order_id,
            "pieces_nested": len(pieces),
            "utilization": nesting_result.get("utilization", 0),
            "fabric_length": nesting_result.get("fabric_length", 0),
            "algorithm": nesting_result.get("algorithm", "unknown"),
        }
        outputs["nesting_report"] = self.file_manager.save_nesting_report(
            order_id, nesting_report
        )

        logger.info(f"Generated all outputs for order {order_id}")
        return outputs

    def _generate_labeled_plt(self, order_id: str, pieces: List[PieceInfo]) -> str:
        """Generate HPGL/PLT file with piece labels"""
        lines = ["IN;"]  # Initialize

        total_pieces = len(pieces)

        for idx, piece in enumerate(pieces, 1):
            piece.piece_number = idx
            piece.total_pieces = total_pieces

            # Select pen
            lines.append("SP1;")

            # Draw piece outline
            if piece.contour:
                first_point = piece.contour[0]
                lines.append(
                    f"PU{int(first_point[0] * 40)},{int(first_point[1] * 40)};"
                )

                for point in piece.contour[1:]:
                    lines.append(f"PD{int(point[0] * 40)},{int(point[1] * 40)};")

                # Close contour
                lines.append(
                    f"PD{int(first_point[0] * 40)},{int(first_point[1] * 40)};"
                )

            # Calculate label position (center of piece)
            if piece.contour:
                min_x = min(p[0] for p in piece.contour)
                max_x = max(p[0] for p in piece.contour)
                min_y = min(p[1] for p in piece.contour)
                max_y = max(p[1] for p in piece.contour)

                center_x = (min_x + max_x) / 2
                center_y = (min_y + max_y) / 2

                # Convert to HPGL units (1mm = 40 units)
                label_x = int(center_x * 40)
                label_y = int(center_y * 40)

                # Add order number label (8mm from center)
                lines.append(f"PU{label_x},{label_y + 320};")  # 8mm up
                lines.append(f"LB{order_id}^;")

                # Add piece name (6mm from center)
                lines.append(f"PU{label_x},{label_y + 160};")  # 4mm up
                lines.append(f"LB{piece.name}^;")

                # Add piece counter (center, 8mm bold)
                lines.append(f"PU{label_x},{label_y};")
                lines.append(f"LB{idx:03d}/{total_pieces:03d}^;")

                # Add grain line arrow if available
                if piece.grainline:
                    arrow_x = label_x + 240  # 6mm right
                    arrow_y = label_y - 160  # 4mm down
                    lines.append(f"PU{arrow_x},{arrow_y};")
                    lines.append(f"PD{arrow_x + 160},{arrow_y + 80};")  # Arrow
                    lines.append(f"PD{arrow_x},{arrow_y + 160};")

            lines.append("PU;")

        lines.append("SP0;")  # Deselect pen
        lines.append("IN;")  # Finalize

        return "\n".join(lines)

    def _generate_labeled_pds(self, order_id: str, pieces: List[PieceInfo]) -> bytes:
        """Generate PDS file with piece labels (simplified format)"""
        # This is a simplified PDS format representation
        # Real implementation would use proper Optitex PDS format

        content_lines = [
            "PDS|VERSION|2.0",
            f"PDS|ORDER|{order_id}",
            f"PDS|CREATED|{datetime.now().isoformat()}",
            f"PDS|PIECES|{len(pieces)}",
            "",
        ]

        for idx, piece in enumerate(pieces, 1):
            piece.piece_number = idx
            piece.total_pieces = len(pieces)

            content_lines.append(f"PIECE|START|{piece.name}|{idx}")

            # Add contour points
            for point in piece.contour:
                content_lines.append(f"POINT|{point[0]}|{point[1]}")

            # Add notches if present
            if piece.notches:
                for notch in piece.notches:
                    content_lines.append(f"NOTCH|{notch[0]}|{notch[1]}")

            # Add labels
            if piece.contour:
                center_x = sum(p[0] for p in piece.contour) / len(piece.contour)
                center_y = sum(p[1] for p in piece.contour) / len(piece.contour)

                # Order number label
                content_lines.append(
                    f"LABEL|{center_x}|{center_y + 8}|{order_id}|8|ORDER"
                )
                # Piece name
                content_lines.append(
                    f"LABEL|{center_x}|{center_y + 4}|{piece.name}|6|NAME"
                )
                # Piece counter
                content_lines.append(
                    f"LABEL|{center_x}|{center_y}|{idx:03d}/{len(pieces):03d}|8|COUNTER|BOLD"
                )

            content_lines.append("PIECE|END")
            content_lines.append("")

        content_lines.append("PDS|END")

        return "\n".join(content_lines).encode("utf-8")

    def _generate_labeled_dxf(self, order_id: str, pieces: List[PieceInfo]) -> str:
        """Generate DXF file with piece labels"""
        lines = [
            "0",
            "SECTION",
            "2",
            "HEADER",
            "9",
            "$ACADVER",
            "1",
            "AC1015",
            "0",
            "ENDSEC",
            "",
            "0",
            "SECTION",
            "2",
            "TABLES",
            "0",
            "TABLE",
            "2",
            "LAYER",
            "70",
            "4",
            "0",
            "LAYER",
            "2",
            "PIECES",
            "70",
            "0",
            "62",
            "7",
            "6",
            "Continuous",
            "0",
            "LAYER",
            "2",
            "LABELS",
            "70",
            "0",
            "62",
            "5",
            "6",
            "Continuous",
            "0",
            "LAYER",
            "2",
            "GRAINLINE",
            "70",
            "0",
            "62",
            "3",
            "6",
            "Continuous",
            "0",
            "ENDTAB",
            "0",
            "ENDSEC",
            "",
            "0",
            "SECTION",
            "2",
            "ENTITIES",
        ]

        for idx, piece in enumerate(pieces, 1):
            piece.piece_number = idx
            piece.total_pieces = len(pieces)

            # Draw piece contour
            if piece.contour:
                lines.extend(["0", "LWPOLYLINE", "8", "PIECES", "66", "1", "70", "1"])

                for point in piece.contour:
                    lines.extend(
                        [
                            "0",
                            "VERTEX",
                            "8",
                            "PIECES",
                            "10",
                            str(point[0]),
                            "20",
                            str(point[1]),
                        ]
                    )

                lines.extend(["0", "SEQEND", "8", "PIECES"])

                # Calculate center
                center_x = sum(p[0] for p in piece.contour) / len(piece.contour)
                center_y = sum(p[1] for p in piece.contour) / len(piece.contour)

                # Add order number label
                lines.extend(
                    [
                        "0",
                        "TEXT",
                        "8",
                        "LABELS",
                        "10",
                        str(center_x),
                        "20",
                        str(center_y + 8),
                        "40",
                        "8",
                        "1",
                        order_id,
                    ]
                )

                # Add piece name
                lines.extend(
                    [
                        "0",
                        "TEXT",
                        "8",
                        "LABELS",
                        "10",
                        str(center_x),
                        "20",
                        str(center_y + 4),
                        "40",
                        "6",
                        "1",
                        piece.name,
                    ]
                )

                # Add piece counter
                lines.extend(
                    [
                        "0",
                        "TEXT",
                        "8",
                        "LABELS",
                        "10",
                        str(center_x),
                        "20",
                        str(center_y),
                        "40",
                        "8",
                        "1",
                        f"{idx:03d}/{len(pieces):03d}",
                    ]
                )

        lines.extend(["0", "ENDSEC", "0", "EOF"])

        return "\n".join(lines)


# Example usage and testing
if __name__ == "__main__":
    # Initialize file manager
    file_mgr = OrderFileManager("test_orders")

    # Generate order ID
    order_id = file_mgr.generate_order_id("CUST-001")
    print(f"Generated order ID: {order_id}")

    # Create folder structure
    folder = file_mgr.create_order_folder(order_id, "CUST-001")
    print(f"Created folder: {folder}")

    # Create sample pieces
    pieces = [
        PieceInfo(
            name="FRONT_PANEL",
            contour=[(0, 0), (50, 0), (50, 60), (0, 60)],
            bounding_box=(0, 0, 50, 60),
        ),
        PieceInfo(
            name="BACK_PANEL",
            contour=[(0, 0), (50, 0), (50, 70), (0, 70)],
            bounding_box=(0, 0, 50, 70),
        ),
        PieceInfo(
            name="SLEEVE_LEFT",
            contour=[(0, 0), (30, 0), (35, 40), (0, 45)],
            bounding_box=(0, 0, 35, 45),
        ),
    ]

    # Generate outputs
    generator = EnhancedOutputGenerator(file_mgr)
    metadata = {
        "customer_id": "CUST-001",
        "garment_type": "jacket",
        "created_at": datetime.now().isoformat(),
    }

    nesting_result = {
        "utilization": 78.5,
        "fabric_length": 120.5,
        "algorithm": "guillotine",
    }

    outputs = generator.generate_all_outputs(order_id, pieces, nesting_result, metadata)

    print("\nGenerated files:")
    for file_type, path in outputs.items():
        print(f"  {file_type}: {path}")

    # Verify all files exist
    all_files = file_mgr.get_all_files(order_id)
    print("\nAll order files:")
    for file_type, path in all_files.items():
        exists = "✓" if path.exists() else "✗"
        print(f"  {exists} {file_type}: {path}")
