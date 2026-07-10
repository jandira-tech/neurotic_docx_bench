#nullable enable

// Copyright (c) Microsoft. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using System.Linq;
using Docxodus;
using Xunit;

namespace Docxodus.Tests;

/// <summary>
/// Tests for the block-metadata read surface on <see cref="DocxSession"/>
/// (<c>GetBlockMetadata</c>, <c>GetBlockMetadatas</c>, <c>GetListMembership</c>,
/// <c>GetSectionInfo</c>). Test IDs follow the <c>BM###</c> prefix convention.
/// </summary>
public class DocxSessionMetadataTests
{
    [Fact]
    public void BM001_GetBlockMetadata_PlainParagraph_ReturnsKindAndScope()
    {
        using var session = new DocxSession(DocxSessionTests.BuildDS001_SimpleTwoParagraphs());
        var anchor = session.Project().AnchorIndex.Values.First(t => t.Anchor.Kind == "p");

        var meta = session.GetBlockMetadata(anchor.Anchor.Id);

        Assert.NotNull(meta);
        Assert.Equal("p", meta!.Kind);
        Assert.Equal("body", meta.Scope);
        Assert.Null(meta.StyleId);
        Assert.Null(meta.StyleName);
        Assert.Null(meta.OutlineLevel);
        Assert.Null(meta.List);
        Assert.False(meta.HasInlineFormatting);
    }

    [Fact]
    public void BM002_GetListMembership_InlineNumPr_BulletList_ReturnsListFacts()
    {
        using var session = new DocxSession(DocxSessionTests.BuildDS002_BulletedList());
        var anchor = session.Project().AnchorIndex.Values.First(t => t.Anchor.Kind == "li");

        var list = session.GetListMembership(anchor.Anchor.Id);

        Assert.NotNull(list);
        Assert.Equal(1, list!.NumId);
        Assert.Equal(0, list.AbstractNumId);
        Assert.Equal(0, list.Level);
        Assert.Equal(NumberFormat.Bullet, list.Format);
        Assert.True(list.IsAutoNumbered);
        Assert.False(list.FromStyle);
        Assert.Null(list.StartOverride);
    }

    [Fact]
    public void BM003_GetListMembership_NotAList_ReturnsNull()
    {
        using var session = new DocxSession(DocxSessionTests.BuildDS001_SimpleTwoParagraphs());
        var anchor = session.Project().AnchorIndex.Values.First(t => t.Anchor.Kind == "p");

        Assert.Null(session.GetListMembership(anchor.Anchor.Id));
    }

    [Fact]
    public void BM004_GetListMembership_StyleInheritedNumPr_SetsFromStyleTrue()
    {
        using var session = new DocxSession(DocxSessionTests.BuildBM_StyleInheritedList());
        var anchor = session.Project().AnchorIndex.Values.First(t => t.Anchor.Kind == "li");

        var list = session.GetListMembership(anchor.Anchor.Id);

        Assert.NotNull(list);
        Assert.True(list!.FromStyle);
        Assert.Equal(1, list.NumId);
        Assert.Equal(0, list.Level);
        Assert.Equal(NumberFormat.Bullet, list.Format);
    }

    [Fact]
    public void BM005_GetSectionInfo_BodyAnchor_ResolvesLandscapeAndHeaders()
    {
        using var session = new DocxSession(DocxSessionTests.BuildBM_LandscapeSection());
        var anchor = session.Project().AnchorIndex.Values.First(t => t.Anchor.Kind == "p");

        var info = session.GetSectionInfo(anchor.Anchor.Id);

        Assert.NotNull(info);
        Assert.Equal(16838, info!.PageWidthTwips);
        Assert.Equal(11906, info.PageHeightTwips);
        Assert.True(info.Landscape);
        Assert.Equal(720, info.MarginTopTwips);
        Assert.Equal(720, info.MarginBottomTwips);
        Assert.Equal(1080, info.MarginLeftTwips);
        Assert.Equal(1080, info.MarginRightTwips);
        Assert.Equal(2, info.Columns);
        Assert.Single(info.HeaderPartUris);
        Assert.Empty(info.FooterPartUris);
    }

    [Fact]
    public void BM006_GetSectionInfo_UnknownAnchor_ReturnsNull()
    {
        using var session = new DocxSession(DocxSessionTests.BuildDS001_SimpleTwoParagraphs());
        Assert.Null(session.GetSectionInfo("p:body:does-not-exist"));
    }

    [Fact]
    public void BM007_GetSectionInfo_NonBodyAnchor_ReturnsNull()
    {
        // The landscape-section fixture has a HeaderPart with one paragraph.
        // That paragraph's anchor lives in scope "hdr1", not "body".
        using var session = new DocxSession(DocxSessionTests.BuildBM_LandscapeSection());
        var hdrAnchor = session.Project().AnchorIndex.Values
            .FirstOrDefault(t => t.Anchor.Scope.StartsWith("hdr", System.StringComparison.Ordinal));
        Assert.NotNull(hdrAnchor);

        Assert.Null(session.GetSectionInfo(hdrAnchor!.Anchor.Id));
    }

    [Fact]
    public void BM008_OutlineLevel_FromHeadingStyle_ResolvesToZeroBasedLevel()
    {
        // BuildDS001 has Heading1..6 styles defined. Apply Heading2 to the first paragraph.
        using var session = new DocxSession(DocxSessionTests.BuildDS001_SimpleTwoParagraphs());
        var anchor = session.Project().AnchorIndex.Values.First(t => t.Anchor.Kind == "p");
        var setStyle = session.SetParagraphStyle(anchor.Anchor.Id, "Heading2");
        Assert.True(setStyle.Success);

        // SetParagraphStyle may have changed the anchor kind from "p" to "h" — re-resolve.
        var freshIndex = session.Project().AnchorIndex;
        var promoted = freshIndex.Values.First(t => t.Anchor.Kind == "h");

        var meta = session.GetBlockMetadata(promoted.Anchor.Id);
        Assert.NotNull(meta);
        Assert.Equal("Heading2", meta!.StyleId);
        Assert.Equal("Heading 2", meta.StyleName);
        Assert.Equal(1, meta.OutlineLevel);  // Heading2 → outlineLvl 1 (0-based)
    }

    [Fact]
    public void BM009_GetBlockMetadatas_Bulk_DedupesAndMapsUnknownToNull()
    {
        using var session = new DocxSession(DocxSessionTests.BuildDS001_SimpleTwoParagraphs());
        var anchors = session.Project().AnchorIndex.Values.Where(t => t.Anchor.Kind == "p").ToList();
        Assert.True(anchors.Count >= 2);

        var ids = new[] {
            anchors[0].Anchor.Id,
            anchors[0].Anchor.Id,         // duplicate
            anchors[1].Anchor.Id,
            "p:body:does-not-exist",
        };

        var map = session.GetBlockMetadatas(ids);

        Assert.Equal(3, map.Count);  // duplicate dropped
        Assert.NotNull(map[anchors[0].Anchor.Id]);
        Assert.NotNull(map[anchors[1].Anchor.Id]);
        Assert.Null(map["p:body:does-not-exist"]);
    }

    [Fact]
    public void BM010_HasInlineFormatting_DetectsBoldRun()
    {
        using var session = new DocxSession(DocxSessionTests.BuildDS001_SimpleTwoParagraphs());
        var anchor = session.Project().AnchorIndex.Values.First(t => t.Anchor.Kind == "p");

        Assert.False(session.GetBlockMetadata(anchor.Anchor.Id)!.HasInlineFormatting);

        var apply = session.ApplyFormat(anchor.Anchor.Id, span: null, new FormatOp { Bold = true });
        Assert.True(apply.Success);

        Assert.True(session.GetBlockMetadata(anchor.Anchor.Id)!.HasInlineFormatting);
    }
}
